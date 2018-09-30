import os.path
from os import pardir as os_pardir
from sys import path as sys_path

sys_path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os_pardir))
