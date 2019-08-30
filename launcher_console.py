from sys import version_info as sys_version_info, exit as sys_exit, argv

try:
    from ui.console_ui import run_console_launcher
finally:
    if sys_version_info[:3] < (3, 7, 4):
        print('Python version 3.7.4 or greater is required')
        sys_exit('Python version error: ' + str(sys_version_info))


if __name__ == '__main__':
    print(argv)

    run_console_launcher()
