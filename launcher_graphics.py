from argparse import ArgumentParser, Namespace
from tkinter import Tk
from contextlib import redirect_stdout as clib_redirect_stdout
from typing import Optional

from vorbis.vorbis_main import PacketsProcessor
from vorbis.ogg import CorruptedFileDataError
from ui.graphics_ui import AudioToolbarFrame, InfoNotebook
from ui.console_ui import exit_with_exception, get_current_version
from launcher_console import init_packets_processor

with clib_redirect_stdout(None):
    from pygame.mixer import (
        pre_init as pygame_mixer_pre_init,
        init as pygame_mixer_init)


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
            description='Processes .ogg audiofile with vorbis coding and '
                        'plays it',
            usage='launcher_console.py [options] filepath')

        parser.add_argument(
            '-v', '--version',
            help="print program's current version number and exit",
            action='version',
            version=_CURRENT_VERSION)

        parser.add_argument(
            'filepath',
            help='path to .ogg audiofile',
            type=str)

        return parser.parse_args()

    arguments: Namespace = _parse_arguments()

    packets_processor: PacketsProcessor = init_packets_processor(
        arguments.filepath)

    pygame_mixer_pre_init(44100, -16, 2, 2048)
    pygame_mixer_init()

    root = Tk()
    root.title("Ogg Vorbis")
    root.minsize(width=375, height=400)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)
    root.columnconfigure(0, weight=1)

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
