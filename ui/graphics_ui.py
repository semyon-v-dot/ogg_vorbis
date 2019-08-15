# built in imports
from os import path as os_path
from sys import (
    exit as sys_exit,
    argv as sys_argv,
    executable as sys_executable,
    version_info as sys_version_info)
from io import BytesIO
from ntpath import basename as ntpath_basename
# graphics and music imports
from tkinter import (
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
from PIL import Image as pil_Image
from PIL.ImageTk import PhotoImage as pil_PhotoImage
from contextlib import redirect_stdout as clib_redirect_stdout
with clib_redirect_stdout(None):
    from pygame.mixer import (
        music as pygame_music,
        Sound as pygame_Sound)


class InfoNotebook(ttk_Notebook):
    '''Class represents two upper info tabs: amplitude and with coverart if \
presented'''
    def __init__(self, filepath, coverart_info, **kw_args):
        super().__init__(**kw_args)
        self.grid(row=0, column=0, sticky='NESW')
        self._filepath = filepath

        self._create_tabs(coverart_info)

        self.grid(sticky='NESW')

    def _create_tabs(self, coverart_info):
        '''Method creates tabs for notebook'''
        self._coverart_frame = tk_Frame(master=self)
        self._coverart_frame.columnconfigure(0, weight=1)
        self._coverart_frame.rowconfigure(0, weight=1)
        self._coverart_canvas = tk_Canvas(master=self._coverart_frame)
        self._coverart_canvas.grid(row=0, column=0)

        final_image = b''
        try:
            final_image = self._decode_base64_to_bytes(coverart_info[1])
        except ValueError as raised_error:
            if str(raised_error) != 'base64 decode failed':
                raise
        else:
            if '=image' in coverart_info[0]:
                coverart_filepath = ntpath_basename(self._filepath)
                coverart_filepath = coverart_filepath.split('.')[0]
                coverart_filepath += '.' + coverart_info[0].split('/')[1]
                coverart_filepath = os_path.join(
                    os_path.dirname(os_path.pardir),
                    'resources',
                    coverart_filepath)
                if not os_path.isfile(coverart_filepath):
                    coverart_file = open(coverart_filepath, 'wb')
                    coverart_file.write(final_image)

                try:
                    self._coverart_image = pil_PhotoImage(
                        pil_Image.open(BytesIO(final_image)))
                except OSError as raised_error:
                    if not str(raised_error).startswith(
                            'cannot identify image file'):
                        raise
                else:
                    self._coverart_canvas.create_image(
                        (0, 0),
                        image=self._coverart_image,
                        anchor='nw')
                    self._coverart_canvas['width'] = (
                        self._coverart_image.width())
                    self._coverart_canvas['height'] = (
                        self._coverart_image.height())

        self.add(self._coverart_frame, text='Coverart')

        self._amplitude_tab = tk_Canvas(master=self)
        self.add(self._amplitude_tab, text='Amplitude')

    def _decode_base64_to_bytes(self, in_data):
        '''Function decodes base64 data to file'''
        assert isinstance(in_data, bytes)

        out_data = b''
        bits_buffer = ''

        for byte in in_data:
            if b'A'[0] <= byte <= b'Z'[0]:
                bits_buffer += bin(byte - 65)[2:].zfill(6)
            elif b'a'[0] <= byte <= b'z'[0]:
                bits_buffer += bin(byte - 71)[2:].zfill(6)
            elif b'0'[0] <= byte <= b'9'[0]:
                bits_buffer += bin(byte + 4)[2:].zfill(6)
            elif bytes([byte]) == b'+':
                bits_buffer += bin(62)[2:].zfill(6)
            elif bytes([byte]) == b'/':
                bits_buffer += bin(63)[2:].zfill(6)
            else:
                raise ValueError('base64 decode failed')

            if len(bits_buffer) > 7:
                out_data += bytes([int(bits_buffer[:8], 2)])
                bits_buffer = bits_buffer[8:]
        if bits_buffer != '':
            out_data += bytes([int(bits_buffer, 2)])

        return out_data


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
