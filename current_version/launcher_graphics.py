from argparse import ArgumentParser
from subprocess import run as subprocess_run
from sys import (
    exit as sys_exit,
    argv as sys_argv,
    executable as sys_executable,
    version_info as sys_version_info)
from launcher_console import CURRENT_VERSION
from tkinter import (
    Tk,
    Frame as tk_Frame,
    Canvas as tk_Canvas,
    Button as tk_Button,
    HORIZONTAL as tk_HORIZONTAL,
    Scale as tk_Scale,
    IntVar as tk_IntVar,
    StringVar as tk_StringVar,
    Label as tk_Label)
from tkinter.ttk import (
    Notebook as ttk_Notebook)
from contextlib import redirect_stdout as clib_redirect_stdout
with clib_redirect_stdout(None):
    from pygame.mixer import (
        pre_init as pygame_mixer_pre_init,
        init as pygame_mixer_init,
        music as pygame_music,
        Sound as pygame_Sound)


class InfoNotebook(ttk_Notebook):
    '''Class represents two upper info tabs: amplitude and with coverart if \
presented'''
    def __init__(self, coverart_base64_data, **kw_args):
        super().__init__(**kw_args)
        self.grid(row=0, column=0, sticky='NESW')

        self._create_tabs(coverart_base64_data)

        self.grid(sticky='NESW')

    def _create_tabs(self, coverart_base64_data):
        '''Method creates tabs for notebook'''
        self._coverart_tab = tk_Canvas(master=self)
        # self._coverart_image =
        self.add(self._coverart_tab, text='Coverart')

        self._amplitude_tab = tk_Canvas(master=self)
        self.add(self._amplitude_tab, text='Amplitude')

    def _decode_base64_to_file(in_data, out_file):
        '''Function decodes base64 data to file'''
        pass


class AudioToolbarFrame(tk_Frame):
    '''Class represents audio tollbar frame'''
    def __init__(self, filepath, **kwargs):
        super().__init__(**kwargs)
        self._filepath = filepath
        self._paused = False
        self._time_offset = 0.0

        self.grid(row=1, column=0, sticky='NESW')
        self.rowconfigure(0, minsize=25)
        self.rowconfigure(2, minsize=25)
        self.columnconfigure(0, minsize=25)
        self.columnconfigure(1, minsize=35)
        self.columnconfigure(2, minsize=50)
        self.columnconfigure(3, weight=1)
        self.columnconfigure(4, minsize=50)

        self._play_button = tk_Button(
            master=self,
            anchor='center',
            text='Play',
            command=self._play_button_hit)
        self._play_button.grid(
            row=1, column=1, sticky='NESW')

        self._create_time_scale_widgets()

        self._volume_scale_var = tk_IntVar()
        self._volume_scale = tk_Scale(
            master=self,
            sliderlength=20,
            from_=100,
            to=0,
            variable=self._volume_scale_var,
            command=self._volume_scale_moved)
        self._volume_scale.grid(row=0, rowspan=3, column=5)
        self._volume_scale_var.set(100)

    def _create_time_scale_widgets(self):
        '''Method create time scale iteslf and related to it widgets'''
        self._time_scale_var = tk_IntVar()
        self._time_scale = tk_Scale(
            master=self,
            orient=tk_HORIZONTAL,
            length=150,
            sliderlength=20,
            variable=self._time_scale_var,
            showvalue=0,
            command=self._time_scale_moved)
        current_track = pygame_Sound(self._filepath)
        self._time_scale['to'] = current_track.get_length()
        self._time_scale.grid(row=1, column=3, sticky='EW')

        self._time_label_var = tk_StringVar()
        self._time_label_var.set('0:00')
        self._time_scale_var.trace(
            'w',
            lambda *args: self._time_label_var.set(
                ''.join([str(self._time_scale_var.get() // 60),
                         ':',
                         str(self._time_scale_var.get() % 60).zfill(2)])))
        self._time_label = tk_Label(
            master=self, textvariable=self._time_label_var)
        self._time_label.grid(row=2, column=3)

    def _play_button_hit(self):
        '''Method contains actions when play button hit'''
        if pygame_music.get_pos() == -1:
            pygame_music.load(self._filepath)

            current_track = pygame_Sound(self._filepath)
            self._time_scale['to'] = current_track.get_length()
            self._play_button['text'] = 'Stop'

            pygame_music.play()
            pygame_music.set_pos(float(self._time_scale_var.get()))
        elif self._paused:
            self._play_button['text'] = 'Stop'
            pygame_music.unpause()
            self._paused = False
        else:
            self._play_button['text'] = 'Play'
            pygame_music.pause()
            self._paused = True

    def _time_scale_moved(self, new_position):
        '''Method contains actions when time scale moved'''
        if pygame_music.get_pos() != -1:
            pygame_music.set_pos(float(new_position))

    def _volume_scale_moved(self, new_position):
        '''Method contains actions when volume scale moved'''
        pygame_music.set_volume(float(new_position) * 0.01)

    def time_scale_tick(self, root):
        '''Method sincs time scale with music progression'''
        if pygame_music.get_pos() != -1:
            if (abs(pygame_music.get_pos() // 1000 - self._time_offset
                    - self._time_scale_var.get()) > 1):
                self._time_offset = float(
                    pygame_music.get_pos() // 1000
                    - self._time_scale_var.get())
            self._time_scale_var.set(
                pygame_music.get_pos() // 1000 - self._time_offset)
        elif self._play_button['text'] == 'Stop':
            self._play_button['text'] = 'Play'
            self._time_scale_var.set(0)

        root.after(100, self.time_scale_tick, root)


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

    info_notebook = InfoNotebook(b'', master=root, padding=(0, 0))
    # raw_image = (  # check if present
    #     packets_processor.logical_streams[0].user_comment_list_strings[-1][9:])

    toolbar_frame = AudioToolbarFrame(
        master=root,
        background='blue',
        filepath=arguments.filepath)
    toolbar_frame.time_scale_tick(root)

    root.mainloop()
