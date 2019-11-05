from unittest import TestCase, main as unittest_main
from os import pardir as os_pardir, remove as os_remove
from os.path import (
    join as os_path_join,
    dirname as os_path_dirname,
    abspath as os_path_abspath,
    exists as os_path_exists)
from sys import path as sys_path
from urllib.request import urlopen
from shutil import copyfileobj as shutil_copyfileobj

sys_path.append(os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    os_pardir))

from vorbis.ogg import PacketsReader


TEST_FILE_1_PATH = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')

TEST_FILE_1_URL: str = (
            r'https://raw.githubusercontent.com/susimus/ogg_vorbis/master/'
            r'tests/test_audiofiles/test_1.ogg')

test_file_1_was_downloaded: bool = False


# noinspection PyPep8Naming
def setUpModule():
    global TEST_FILE_1_PATH

    if not os_path_exists(TEST_FILE_1_PATH):
        global test_file_1_was_downloaded, TEST_FILE_1_URL

        test_file_1_was_downloaded = True

        with urlopen(TEST_FILE_1_URL) as response, (
                open(TEST_FILE_1_PATH, 'wb')) as out_file:
            shutil_copyfileobj(response, out_file)


# noinspection PyPep8Naming
def tearDownModule():
    global test_file_1_was_downloaded

    if test_file_1_was_downloaded:
        global TEST_FILE_1_PATH

        os_remove(TEST_FILE_1_PATH)

class PacketReadingTest(TestCase):
    @staticmethod
    def test_correct_filename():
        packets_reader = PacketsReader(TEST_FILE_1_PATH)
        packets_reader.close_file()

    @staticmethod
    def test_read_packet():
        packets_reader = PacketsReader(TEST_FILE_1_PATH)
        packets_reader.read_packet()

        packets_reader.close_file()

    @staticmethod
    def test_pages_consistency():
        packets_reader = PacketsReader(TEST_FILE_1_PATH)

        current_page = 0
        try:
            while True:
                packet_and_its_pages = packets_reader.read_packet()
                for page in packet_and_its_pages[1]:
                    assert current_page == page, (
                        str(current_page) + ' != ' + str(page))
                    current_page += 1
        except EOFError as raised_error:
            assert str(raised_error) == 'File end reached'

        packets_reader.close_file()

    @staticmethod
    def test_moving_byte_pointer():
        packets_reader = PacketsReader(TEST_FILE_1_PATH)
        packets_reader.move_byte_position(352363)

        current_page = 54
        try:
            while True:
                packet_and_its_pages = packets_reader.read_packet()
                for page in packet_and_its_pages[1]:
                    assert current_page == page, (
                        str(current_page) + ' != ' + str(page))
                    current_page += 1
        except EOFError as raised_error:
            assert str(raised_error) == 'File end reached'

        packets_reader.close_file()


if __name__ == '__main__':
    unittest_main()
