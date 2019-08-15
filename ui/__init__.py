from sys import version_info as sys_version_info, exit as sys_exit


if (sys_version_info.major < 3
            or (sys_version_info.major == 3 and sys_version_info.minor < 7)):
        sys_exit('Python version 3.7 or upper is required')