from os import path as os_path
from unittest import TestCase

import tests.__init__  # Without this anytask won't see tests
from vorbis.ogg import PacketsReader


PATH_ORDINARY_TEST_1 = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
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
