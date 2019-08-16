from argparse import ArgumentParser, Namespace
from typing import Optional

from vorbis.vorbis_main import PacketsProcessor, EndOfPacketException
from vorbis.ogg import CorruptedFileDataError
from ui.console_ui import (
    generate_ident_header,
    generate_setup_header,
    generate_comment_header,
    get_current_version,
    exit_with_exception)


_PRINT_HEADER_SWITCH = {
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


def init_packets_processor(filepath: str) -> PacketsProcessor:
    """Initializes packets processor

    If initialization is failed then method prints exception details and
    closes process"""
    result_packets_processor: Optional[PacketsProcessor] = None
    try:
        result_packets_processor = PacketsProcessor(filepath)
        result_packets_processor.process_headers()

    except FileNotFoundError as occurred_exc:
        exit_with_exception(
            "File not found: " + arguments.filepath,
            occurred_exc)

    except IsADirectoryError as occurred_exc:
        exit_with_exception(
            'Directory name given: ' + arguments.filepath,
            occurred_exc)

    except PermissionError as occurred_exc:
        exit_with_exception(
            'No access to file: ' + arguments.filepath,
            occurred_exc)

    except OSError as occurred_exc:
        exit_with_exception(
            'File handling is impossible: ' + arguments.filepath,
            occurred_exc)

    except CorruptedFileDataError as occurred_exc:
        exit_with_exception(
            "File data is corrupted",
            occurred_exc)

    except EndOfPacketException as occurred_exc:
        exit_with_exception(
            "File data is corrupted",
            occurred_exc)

    except Exception as occurred_exc:
        exit_with_exception(
            "Some exception occurred in process of data reading",
            occurred_exc)

    if result_packets_processor is None:
        exit_with_exception(
            "Some exception occurred in process of data reading",
            Exception("Packets processor initialization failed"))

    return result_packets_processor


if __name__ == '__main__':
    _CURRENT_VERSION: Optional[str] = None
    try:
        _CURRENT_VERSION = get_current_version()
    except OSError as occurred_exc:
        exit_with_exception(
            'Cannot read "data.ini" file',
            occurred_exc)

    if _CURRENT_VERSION is None:
        exit_with_exception(
            'Error during "data.ini" file reading',
            CorruptedFileDataError("Cannot get version"))

    def _parse_arguments() -> Namespace:
        parser = ArgumentParser(
            description='Process .ogg audiofile with vorbis coding and output '
                        'headers data in console',
            usage='launcher_console.py [options] filepath')

        parser.add_argument(
            '-v', '--version',
            help="print program's current version number and exit",
            action='version',
            version=_CURRENT_VERSION)

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

        return parser.parse_args()

    arguments: Namespace = _parse_arguments()

    packets_processor: PacketsProcessor = init_packets_processor(
        arguments.filepath)

    if not (arguments.ident or arguments.comment or arguments.setup):
        arguments.ident = arguments.comment = True

    if arguments.ident:
        _PRINT_HEADER_SWITCH['ident'](
            packets_processor.logical_streams[0],
            arguments.explain)
    if arguments.comment:
        _PRINT_HEADER_SWITCH['comment'](
            packets_processor.logical_streams[0],
            arguments.explain)
    if arguments.setup:
        _PRINT_HEADER_SWITCH['setup'](
            packets_processor.logical_streams[0],
            arguments.explain)

    packets_processor.close_file()
