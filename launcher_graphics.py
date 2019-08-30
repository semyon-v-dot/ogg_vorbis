from sys import version_info as sys_version_info, exit as sys_exit

try:
    from ui.graphics_ui import run_graphics_launcher
finally:
    if sys_version_info[:3] < (3, 7, 4):
        print('Python version 3.7.4 or greater is required')
        sys_exit('Python version error: ' + str(sys_version_info))


if __name__ == '__main__':
    run_graphics_launcher()
