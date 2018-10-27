from os import (
    pardir as os_pardir,
    path as os_path)
from sys import path as sys_path

sys_path.append(os_path.join(os_path.dirname(os_path.abspath(__file__)),
                             os_pardir))
