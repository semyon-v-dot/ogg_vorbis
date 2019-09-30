from argparse import Namespace, ArgumentParser
from configparser import (
    ConfigParser, ParsingError as configparser_ParsingError)
from sys import exit as sys_exit
from typing import Optional
from os.path import (
    split as os_path_split,
    join as os_path_join)

from vorbis.vorbis_main import (
    PacketsProcessor, CorruptedFileDataError, EndOfPacketException)


def _generate_ident_header(logical_stream, explain_needed):
    """Function generate identification header from input [logical_stream] \
internal values"""
    return ''.join([
        f'''
{'-'*8}IDENTIFICATION HEADER INFO:

[audio_channels] = {logical_stream.audio_channels}\n''',
        (' ' * 4) + 'Number of audio channels\n' if explain_needed else '',
        f'''[audio_sample_rate] = {logical_stream.audio_sample_rate}\n''',
        (' ' * 4) + 'Value of audio sample rate\n' if explain_needed else '',
        f'''
[bitrate_maximum] = {logical_stream.bitrate_maximum}
[bitrate_nominal] = {logical_stream.bitrate_nominal}
[bitrate_minimum] = {logical_stream.bitrate_minimum}''',
        '''
    About bitrates values (0 means value is unset):
        * All three fields set to the same value implies a fixed rate,
          or tightly bounded, nearly fixed-rate bitstream
        * Only nominal set implies a VBR or ABR stream
          that averages the nominal bitrate
        * Maximum and or minimum set implies a VBR bitstream
          that obeys the bitrate limits
        * None set indicates the encoder does not care to speculate.'''
        if explain_needed else '',
        f'''\n
[blocksize_0] = {logical_stream.blocksize_0}
[blocksize_1] = {logical_stream.blocksize_1}''',
        '''
    These two values are 2 exponent. They represents blocksizes of vorbis
    window function''' if explain_needed else ''])


def _generate_comment_header(logical_stream, explain_needed):
    """Function generate comment header from input [logical_stream] \
internal values"""
    output_ = ''.join((f'''
{'-'*8}COMMENT HEADER INFO:

[comment_header_decoding_failed] = \
{logical_stream.comment_header_decoding_failed}''',
                       '''
    Indicates if decoder failed while decoding comment header. If 'True' then
    strings below may be damaged, nonsensical at all or just absent.
    Note: strings bigger than 1000 characters will be cut and marked with [...]
    at the end for convenient look''' if explain_needed else '',
                       '''
[vendor_string]
    Main comment string. Contains:
'''))

    output_ += _process_comment_lines(logical_stream, 'vendor_string')
    output_ += '''\
[user_comment_list_strings]
    User comment strings. May be not set. Contains:
'''
    output_ += \
        _process_comment_lines(logical_stream, 'user_comment_list_strings')

    return output_.rstrip()


def _process_comment_lines(logical_stream, lines_name):
    """Function process comment lines into readable state"""
    if len(getattr(logical_stream, lines_name, [])) == 0:
        return "        Nothing. String(s) is(are) absent\n"

    lines = list(getattr(logical_stream, lines_name))
    if isinstance(lines, str):
        lines = [lines]

    lines[0] = (" " * 8) + lines[0]
    for i, line_ in enumerate(lines):
        if len(line_) > 1000:
            lines[i] = lines[i][:1000] + "[...]"

    separator = "\n" + (" " * 8)

    return separator.join(lines) + '\n'


# WouldBeBetter: Complete '_generate_setup_header'
def _generate_setup_header(logical_stream, explain_needed: bool):
    """Function generate setup header from input [logical_stream] \
internal values"""
    output_info = ''.join((f'''
{'-'*8}SETUP HEADER INFO:

[vorbis_floor_types] = {logical_stream.vorbis_floor_types}''',
                           '''
        Vorbis encodes a spectral ’floor’ vector for each PCM channel. This
    vector is a low-resolution representation of the audio spectrum for the
    give-n channel in the current frame, generally used akin to a whitening
    filter. It is named a ’floor’ because the Xiph.Org reference encoder has
    historically used it as a unit-baseline for spectral resolution.
        A floor encoding may be of two types. Floor 0 uses a packed LSP
    representation on a dB amplitude scale and Bark frequency scale. Floor 1
    represents the curve as a piecewise linear interpolated representation on
    a dB amplitude scale and linear frequency scale.'''
                           if explain_needed else '',
                           '''
[vorbis_floor_configurations]:
    '''))
    output_info += f'\n{" "*4}'.join(
        [str(config) for config in
            logical_stream.vorbis_floor_configurations])

    output_info += ''.join([f'''

[vorbis_residue_types] = {logical_stream.vorbis_residue_types}''',
                            '''
        A residue vector represents the fine detail of the audio spectrum of
    one channel in an audio frame after the encoder subtracts the floor curve
    and performs any channel coupling. A residue vector may represent spectral
    lines, spectral magnitude, spectral phase or hybrids as mixed by channel
    coupling. The exact semantic content of the vector does not matter to the
    residue abstraction.
        Whatever the exact qualities, the Vorbis residue abstraction codes the
    residue vectors into the bitstream packet, and then reconstructs the
    vectors during decode. Vorbis makes use of three different encoding
    variants (numbered 0, 1 and 2) of the same basic vector encoding
    abstraction.''' if explain_needed else '',
                            '''
[vorbis_residue_configurations]:
    '''])
    output_info += f'\n{" "*4}'.join(
        [str(config) for config in
            logical_stream.vorbis_residue_configurations])

    output_info += ''.join([f'''

Mappings:
        A mapping contains a channel coupling description and a list of submaps
    that bundle sets of channel vectors together for grouped encoding and
    decoding. These submaps are not references to external components; the
    submap list is internal and specific to a mapping.
        A ’submap’ is a configuration/grouping that applies to a subset of
    floor and residue vectors within a mapping. The submap functions as a last
    layer of indirection such that specific special floor or residue settings
    can be applied not only to all the vectors in a given mode, but also
    specific vectors in a specific mode. Each submap specifies the proper
    floor and residue instance number to use for decoding that submap’s
    spectral floor and spectral residue vectors.'''
                            if explain_needed else '\n',
                            '''
[vorbis_mapping_configurations]:
    '''])
    output_info += f'\n{" "*4}'.join(
        [str(config) for config in
            logical_stream.vorbis_mapping_configurations])

    output_info += ''.join([f'''

Modes:
        Each Vorbis frame is coded according to a master ’mode’.
    A bitstream may use one or many modes.
        The mode mechanism is used to encode a frame according to one of
    multiple possible methods with the intention of choosing a method best
    suited to that frame. Different modes are, e.g. how frame size is changed
    from frame to frame. The mode number of a frame serves as a top level
    configuration switch for all other specific aspects of frame decode.
       A ’mode’ configuration consists of a frame size setting, window type
    (always 0, the Vorbis window, in Vorbis I), transform type (always type 0,
    the MDCT, in Vorbis I) and a mapping number. The mapping number specifies
    which mapping configuration instance to use for low-level packet decode
    and synthesis.''' if explain_needed else '\n',
                            '''
[vorbis_mode_configurations]:
    '''])
    output_info += f'\n{" "*4}'.join(
        [' '.join([str(i) + ')',
                   'vorbis_mode_blockflag', '=', str(config[0]),
                   'vorbis_mode_mapping', '=', str(config[1])])
            for i, config in enumerate(
                logical_stream.vorbis_mode_configurations)])

    return output_info


def get_current_version() -> str:
    """Gives current version str

    Gives version based on 'config.ini' in application's folder. If data is
    corrupted then "Cannot read 'config.ini' file" str returns
    """
    config: ConfigParser = ConfigParser()

    current_dir: str
    parent_dir: str

    current_dir, _ = os_path_split(__file__)
    parent_dir, _ = os_path_split(current_dir)

    try:
        config.read(os_path_join(parent_dir, 'config.ini'))
    except configparser_ParsingError:
        pass

    if 'VERSION' not in config or 'current_version' not in config['VERSION']:
        return "Cannot read 'config.ini' file"
    else:
        return config['VERSION']['current_version']


def init_packets_processor(
        filepath: str, arguments: Namespace) -> PacketsProcessor:
    """Initializes packets processor

    If initialization is failed then method prints exception details and
    closes process"""
    result_packets_processor: Optional[PacketsProcessor] = None
    try:
        result_packets_processor = PacketsProcessor(filepath)
        result_packets_processor.process_headers()

    except FileNotFoundError as occurred_exc:
        exit_with_exception(
            "File not found: " + filepath,
            occurred_exc,
            arguments.debug)

    except IsADirectoryError as occurred_exc:
        exit_with_exception(
            'Directory name given: ' + filepath,
            occurred_exc,
            arguments.debug)

    except PermissionError as occurred_exc:
        exit_with_exception(
            'No access to file: ' + filepath,
            occurred_exc,
            arguments.debug)

    except OSError as occurred_exc:
        exit_with_exception(
            'File handling is impossible: ' + filepath,
            occurred_exc,
            arguments.debug)

    except (CorruptedFileDataError, EndOfPacketException) as occurred_exc:
        exit_with_exception(
            "File data is corrupted",
            occurred_exc,
            arguments.debug)

    except Exception as occurred_exc:
        exit_with_exception(
            "Some exception occurred in process of data reading",
            occurred_exc,
            arguments.debug)

    if result_packets_processor is None:
        exit_with_exception(
            "Some exception occurred in process of data reading",
            Exception("Packets processor initialization failed"),
            arguments.debug)

    return result_packets_processor


def exit_with_exception(
        info_for_user: str,
        input_exception: Exception,
        debugging_mode: bool):
    """Exits with exception

    Prints info to stdout for user and to stderr for debugging. Instead of
    error codes, 'error strings' are used. 'Error strings' have format:
    '\n' + (exception name) + ': ' + (exception args)
    """
    print(info_for_user)

    if debugging_mode:
        sys_exit(
            "\n"
            + input_exception.__class__.__name__
            + ": "
            + str(input_exception))
    else:
        sys_exit(0)


def run_console_launcher():
    def _parse_arguments() -> Namespace:
        parser = ArgumentParser(
            description='Process .ogg audiofile with vorbis coding and output '
                        'headers data in console',
            usage='launcher_console.py [options] filepath')

        parser.add_argument(
            '--version',
            help="print program's current version number and exit",
            action='version',
            version=get_current_version())

        parser.add_argument(
            '--explain',
            help='show explanations in output about headers data',
            action='store_true')

        parser.add_argument(
            '-d', '--debug',
            help='turn on debug mode',
            action='store_true')

        parser.add_argument(
            '-i', '--ident',
            help='print identification header info',
            action='store_true')

        parser.add_argument(
            '-s', '--setup',
            help='print setup header info',
            action='store_true')

        parser.add_argument(
            '-c', '--comment',
            help='print comment header info',
            action='store_true')

        parser.add_argument(
            'filepath',
            help='path to .ogg audiofile',
            type=str)

        return parser.parse_args()

    arguments: Namespace = _parse_arguments()

    packets_processor: PacketsProcessor = init_packets_processor(
        arguments.filepath, arguments)

    if not (arguments.ident or arguments.comment or arguments.setup):
        arguments.ident = arguments.comment = True

    if arguments.ident:
        print(_generate_ident_header(
            packets_processor.logical_streams[0],
            arguments.explain))

    if arguments.comment:
        print(_generate_comment_header(
            packets_processor.logical_streams[0],
            arguments.explain))

    if arguments.setup:
        print(_generate_setup_header(
            packets_processor.logical_streams[0],
            arguments.explain))

    packets_processor.close_file()
