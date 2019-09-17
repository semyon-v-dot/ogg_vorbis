from unittest import TestCase, main as unittest_main
from os import pardir as os_pardir
from os.path import (
    join as os_path_join,
    dirname as os_path_dirname,
    abspath as os_path_abspath)
from sys import path as sys_path

sys_path.append(os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    os_pardir))

from vorbis.ogg import PacketsReader


PATH_ORDINARY_TEST_1 = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')


class PacketReadingTest(TestCase):
    @staticmethod
    def test_correct_filename():
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
        packets_reader.close_file()

    @staticmethod
    def test_read_packet():
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
        packets_reader.read_packet()

        packets_reader.close_file()

    @staticmethod
    def test_pages_consistency():
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)

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
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
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
