from os import (
    pardir as os_pardir,
    path as os_path)
from sys import path as sys_path


_absolute_path_to_parent_dir: str = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    os_pardir)
if _absolute_path_to_parent_dir not in sys_path:
    sys_path.append(_absolute_path_to_parent_dir)
