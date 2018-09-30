import io
import sys
import os
import unittest
import pathmagic
from vorbis.ogg import PacketsReader


PATH_ORDINARY_TEST_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'ordinary_test_1.ogg')


class PacketReadingTest(unittest.TestCase):
    def test_incorrect_filename(self):
        with self.assertRaises(SystemExit) as cm:
            captured_output = io.StringIO()
            sys.stdout = captured_output

            packets_reader = PacketsReader('asdsaddas')

            sys.stdout = sys.__stdout__

        self.assertEqual(cm.exception.code, 3)

    def test_correct_filename(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)

    def test_read_packet(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)

        packets_reader.read_packet()

    def test_pages_consistency(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)

        pages = []
        try:
            while True:
                packet_and_its_pages = packets_reader.read_packet()
                pages += packet_and_its_pages[1]
        except EOFError:
            pass

        counter = 0
        for page in pages:
            self.assertEqual(page, counter)
            counter += 1

    def test_moving_byte_pointer(self):
        packets_reader = PacketsReader(PATH_ORDINARY_TEST_1)
        packets_reader.move_byte_pointer(352363)

        pages = []
        try:
            while True:
                packet_and_its_pages = packets_reader.read_packet()
                pages += packet_and_its_pages[1]
        except EOFError:
            pass

        counter = 54
        for page in pages:
            self.assertEqual(page, counter)
            counter += 1


if __name__ == '__main__':
    unittest.main()
