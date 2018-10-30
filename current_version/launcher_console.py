# built in imports
from argparse import ArgumentParser
from subprocess import run as subprocess_run
from sys import (
    exit as sys_exit,
    argv as sys_argv,
    executable as sys_executable,
    version_info as sys_version_info)
# internal imports
from vorbis.vorbis_main import (
    PacketsProcessor, FileNotVorbisError, EndOfPacketError)
from vorbis.ogg import (
    CorruptedFileDataError,
    FileNotAnOggContainerError,
    UnexpectedEndOfFileError)
from ui.console_ui import (
    generate_ident_header,
    generate_setup_header,
    generate_comment_header)


CURRENT_VERSION = 'ogg_vorbis 4'
PRINT_HEADER = {
    'ident':
        lambda logical_stream, explain_needed:
            print(generate_ident_header(logical_stream, explain_needed)),
    'comment':
        lambda logical_stream, explain_needed:
            print(generate_comment_header(logical_stream, explain_needed)),
    'setup':
        lambda logical_stream, explain_needed:
            print(generate_setup_header(logical_stream, explain_needed))
}


if __name__ == '__main__':
    if (sys_version_info.major < 3
            or (sys_version_info.major == 3 and sys_version_info.minor < 7)):
        print('Python version 3.7 or upper is required')
        sys_exit(0)

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
        '--debug',
        help='start program in debug mode',
        action='store_true')
    parser.add_argument(
        '--explain',
        help='show explanations in output about headers data',
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

    if not arguments.debug and __debug__:
        subprocess_run([sys_executable, '-O'] + sys_argv)
        sys_exit(0)

    try:
        packets_processor = PacketsProcessor(arguments.filepath)
        packets_processor.process_headers()
    except CorruptedFileDataError as corrupted_data_error:
        # print("File data is corrupted")

        if isinstance(corrupted_data_error, UnexpectedEndOfFileError):
            sys_exit('End of file unexpectedly reached')

        sys_exit(corrupted_data_error)
    except EndOfPacketError:
        print("File data is corrupted")
        sys_exit('End of packet condition unexpectedly triggered')
    except Exception as error_:
        sys_exit(error_)

    if not (arguments.ident or arguments.comment or arguments.setup):
        arguments.ident = arguments.comment = True

    if arguments.ident:
        PRINT_HEADER['ident'](
            packets_processor.logical_streams[0],
            arguments.explain)
    if arguments.comment:
        PRINT_HEADER['comment'](
            packets_processor.logical_streams[0],
            arguments.explain)
    if arguments.setup:
        PRINT_HEADER['setup'](
            packets_processor.logical_streams[0],
            arguments.explain)

    packets_processor.close_file()
