from os import path as os_path
from unittest import (
    main as unittest_main,
    TestCase as unittest_TestCase)
import pathmagic
from vorbis.ogg import PacketsReader


PATH_ORDINARY_TEST_1 = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')


class PacketReadingTest(unittest_TestCase):
    def test_correct_filename(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
        packets_reader.close_file()

    def test_read_packet(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
        packets_reader.read_packet()

        packets_reader.close_file()

    def test_pages_consistency(self):
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

    def test_moving_byte_pointer(self):
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
