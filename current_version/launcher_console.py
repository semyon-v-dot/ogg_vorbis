from argparse import ArgumentParser
from subprocess import run as subprocess_run
from sys import (
    exit as sys_exit, 
    argv as sys_argv,
    executable as sys_executable)
from vorbis.vorbis_main import PacketsProcessor, FileNotVorbisError
from vorbis.ogg import (
    CorruptedFileDataError, 
    FileNotAnOggContainerError, 
    UnexpectedEndOfFileError)


def generate_ident_header(logical_stream):
    '''Function generate identification header from input [logical_stream] \
internal values'''
    return f'''
{'-'*8}IDENTIFICATION HEADER INFO:

[audio_channels] = {logical_stream.audio_channels}
    Number of audio channels
[audio_sample_rate] = {logical_stream.audio_sample_rate}
    Value of audio sample rate

[bitrate_maximum] = {logical_stream.bitrate_maximum}
[bitrate_nominal] = {logical_stream.bitrate_nominal}
[bitrate_minimum] = {logical_stream.bitrate_minimum}
    About bitrates values (0 means value is unset):
        * All three fields set to the same value implies a fixed rate,
          or tightly bounded, nearly fixed-rate bitstream
        * Only nominal set implies a VBR or ABR stream
          that averages the nominal bitrate
        * Maximum and or minimum set implies a VBR bitstream
          that obeys the bitrate limits
        * None set indicates the encoder does not care to speculate.

[blocksize_0] = {logical_stream.blocksize_0}
[blocksize_1] = {logical_stream.blocksize_1}
    These two values are 2 exponent. They represents blocksizes of vorbis
    window function\
'''


def generate_comment_header(logical_stream):
    '''Function generate comment header from input [logical_stream] \
internal values'''
    output_ = f'''
{'-'*8}COMMENT HEADER INFO:

[comment_header_decoding_failed] = \
{logical_stream.comment_header_decoding_failed}
    Indicates if decoder failed while decoding comment header. If 'True' then
    strings below may be damaged, nonsensical at all or just absent.
    Note: strings bigger than 1000 characters will be cut and marked with [...]
    at the end for convenient look
[vendor_string]
    Main comment string. Contains:
'''

    output_ += _process_comment_lines(logical_stream, 'vendor_string')
    output_ += '''\
[user_comment_list_strings]
    User comment strings. May be not set. Contains:
'''
    output_ += \
        _process_comment_lines(logical_stream, 'user_comment_list_strings')

    return output_.rstrip()


def _process_comment_lines(logical_stream, lines_name):
    '''Function process comment lines into readable state'''
    if len(getattr(logical_stream, lines_name, [])) == 0:
        return "        Nothing. String(s) is(are) absent\n"

    lines = list(getattr(logical_stream, lines_name))
    if isinstance(lines, str):
        lines = [lines]

    lines[0] = " "*8 + lines[0]
    for i, line_ in enumerate(lines):
        if len(line_) > 1000:
            lines[i] = lines[i][:1000] + "[...]"
    
    separator = "\n" + " "*8

    return separator.join(lines) + '\n'


def generate_setup_header(logical_stream):  # WIP
    '''Function generate setup header from input [logical_stream] \
internal values'''
    return f'''
{'-'*8}SETUP HEADER INFO:

NOT IMPLEMENTED YET
'''


def _clear_argv_for_debug(old_argv):
    '''Function clears input argv from any "--debug" or "-d" commands'''
    new_argv = list(
        filter(lambda argument: argument != '--debug', old_argv))
    for i, argument in enumerate(new_argv):
        if argument[0] == '-' and argument[1] != '-':
            new_argv[i] = ''.join(list(
                filter(lambda letter: letter != 'd', argument)))

    return new_argv


CURRENT_VERSION = 'ogg_vorbis 3'
PRINT_HEADER = {
    'ident': 
        lambda logical_stream: print(generate_ident_header(logical_stream)),
    'comment':
        lambda logical_stream: print(generate_comment_header(logical_stream)),
    'setup': 
        lambda logical_stream: print(generate_setup_header(logical_stream))
}


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Process .ogg audiofile with vorbis coding and '
                    'output headers data in console',
        usage='launcher_console.py [options] filepath')

    parser.add_argument(
        '-v', '--version',
        help="print program's current version number and exit",
        action='version',
        version=CURRENT_VERSION)

    parser.add_argument(
        '-d', '--debug',
        help='start program in debug mode',
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

    arguments = parser.parse_args()

    if not arguments.debug and __debug__ == True:
        subprocess_run([sys_executable, '-O'] + sys_argv)
        sys_exit(0)

    try:
        packets_processor = PacketsProcessor(arguments.filepath)
        packets_processor.process_headers()
    except CorruptedFileDataError as corrupted_data_error:
        print("File data is corrupted")
        
        if isinstance(corrupted_data_error, UnexpectedEndOfFileError):
            sys_exit('End of file unexpectedly reached')
        
        sys_exit(corrupted_data_error)
    except (FileNotVorbisError, FileNotAnOggContainerError,
            FileNotFoundError, IsADirectoryError, PermissionError, OSError
            ) as error_: 
        sys_exit(error_)

    if not (arguments.ident or arguments.comment or arguments.setup):
        arguments.ident = arguments.comment = True

    if arguments.ident:
        PRINT_HEADER['ident'](packets_processor.logical_streams[0])
    if arguments.comment:
        PRINT_HEADER['comment'](packets_processor.logical_streams[0])
    if arguments.setup:
        PRINT_HEADER['setup'](packets_processor.logical_streams[0])

    packets_processor.close_file()
