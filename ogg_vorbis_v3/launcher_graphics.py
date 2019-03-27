from argparse import ArgumentParser
from ogg_vorbis_cui import *
from tkinter import (
    Tk, 
    Frame as tk_Frame)
from tkinter.ttk import Notebook as ttk_Notebook



class HeadersInfoNotebook(ttk_Notebook):
    def __init__(self, master=None):
        super().__init__(master)
    
class AudioToolbarFrame(tk_Frame):
    def __init__(self, master=None, width=100, height=100):
        super().__init__(master)

if __name__ == '__main__':
    parser = ArgumentParser(
        description='Process .ogg audiofile with vorbis coding and '
                    'output headers data in console')

    parser.add_argument(
        '--version',
        help="print program's current version number",
        action='version',
        version=CURRENT_VERSION)
        
    parser.add_argument(
        '--filepath',
        help='path to .ogg audiofile',
        type=str)
        
    args = parser.parse_args()
    
    root = Tk()
    root.title("Ogg Vorbis V.2")

    headers_info_frame = \
        tk_Frame(master=root, width=600, height=400, background='black')
    headers_info_frame.grid(row=0, sticky='NESW')
    
    headers_info_notebook = HeadersInfoNotebook(master=headers_info_frame)
    headers_info_notebook.grid(row=0, sticky='NESW')
    
    ident_header_tab = tk_Frame(master=headers_info_notebook)
    headers_info_notebook.add(ident_header_tab, text='Identification')
    
    comment_header_tab = tk_Frame(master=headers_info_notebook)
    headers_info_notebook.add(comment_header_tab, text='Comment')
    
    #  audio_toolbar_frame 
    
    root.mainloop()
    