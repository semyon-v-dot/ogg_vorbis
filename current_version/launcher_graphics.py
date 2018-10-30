# built in imports
from argparse import ArgumentParser
from subprocess import run as subprocess_run
from sys import (
    exit as sys_exit,
    argv as sys_argv,
    executable as sys_executable,
    version_info as sys_version_info)
# internal imports
from launcher_console import CURRENT_VERSION
from vorbis.vorbis_main import (
    PacketsProcessor, FileNotVorbisError, EndOfPacketError, DataReader)
from vorbis.ogg import (
    CorruptedFileDataError,
    FileNotAnOggContainerError,
    UnexpectedEndOfFileError)
from ui.graphics_ui import AudioToolbarFrame, InfoNotebook
# graphics and music imports
from tkinter import Tk
from contextlib import redirect_stdout as clib_redirect_stdout
with clib_redirect_stdout(None):
    from pygame.mixer import (
        pre_init as pygame_mixer_pre_init,
        init as pygame_mixer_init)


if __name__ == '__main__':
    if (sys_version_info.major < 3
            or (sys_version_info.major == 3 and sys_version_info.minor < 7)):
        print('Python version 3.7 or upper is required')
        sys_exit(0)

    parser = ArgumentParser(
        description='Process .ogg audiofile with vorbis coding and '
                    'play it',
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
        'filepath',
        help='path to .ogg audiofile',
        type=str)

    arguments = parser.parse_args()

    if not arguments.debug and __debug__:
        subprocess_run([sys_executable, '-O'] + sys_argv)
        sys_exit(0)

    pygame_mixer_pre_init(44100, -16, 2, 2048)
    pygame_mixer_init()

    root = Tk()
    root.title("Ogg Vorbis V.4")
    root.minsize(width=375, height=400)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    root.columnconfigure(0, weight=1)

    try:
        packets_processor = PacketsProcessor(arguments.filepath)
        packets_processor.process_headers()
    except CorruptedFileDataError as corrupted_data_error:
        print("File data is corrupted")

        if isinstance(corrupted_data_error, UnexpectedEndOfFileError):
            sys_exit('End of file unexpectedly reached')

        sys_exit(corrupted_data_error)
    except EndOfPacketError:
        print("File data is corrupted")
        sys_exit('End of packet condition unexpectedly triggered')
    except Exception as error_:
        sys_exit(error_)

    raw_image_info = ('', b'')
    if (hasattr(packets_processor.logical_streams[0],
                'user_comment_list_strings')):
        coverart_index = -1
        for i, comment_str in enumerate(
                packets_processor.logical_streams[0]
                .user_comment_list_strings):
            if (comment_str.startswith('COVERARTMIME=')
                    and len(packets_processor.logical_streams[0]
                            .user_comment_list_strings) > i + 1
                    and packets_processor.logical_streams[0]
                    .user_comment_list_strings[i + 1]
                    .startswith('COVERART=')):
                coverart_index = i
                break
        if coverart_index != -1:
            raw_image_info = (
                packets_processor.logical_streams[0]
                .user_comment_list_strings[coverart_index],
                packets_processor.logical_streams[0]
                .user_comment_list_strings[coverart_index + 1].encode()[9:])
    info_notebook = InfoNotebook(
        coverart_info=raw_image_info,
        filepath=arguments.filepath,
        master=root,
        padding=(0, 0))

    toolbar_frame = AudioToolbarFrame(
        master=root,
        background='blue',
        filepath=arguments.filepath)
    toolbar_frame.time_scale_tick(root)

    root.mainloop()
