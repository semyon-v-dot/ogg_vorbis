from os.path import (
    split as os_path_split,
    abspath as os_path_abspath)
from sys import path as sys_path

ui_folder_path, _ = os_path_split(os_path_abspath(__file__))

ogg_vorbis_root, _ = os_path_split(ui_folder_path)

sys_path.append(ogg_vorbis_root)
