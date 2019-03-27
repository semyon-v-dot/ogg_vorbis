import unittest
import sys
import os
import pathmagic
from vorbis.vorbis_main import DataReader
from vorbis.vorbis_main import EndOfPacketError
from vorbis.vorbis_main import PacketsProcessor
from vorbis.helper_funcs import *


PATH_ORDINARY_TEST_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'ordinary_test_1.ogg')


class DataReaderTests(unittest.TestCase):
    def test_read_some_bytes(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72\x62\x69\x73'
        readed_bytes = b''
        for i in range(6):
            readed_bytes += data_reader.read_byte()

        self.assertEqual(readed_bytes, b'\x76\x6f\x72\x62\x69\x73')

    def test_read_some_extra_bytes(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72\x62\x69\x73'
        try:
            for i in range(7):
                data_reader.read_byte()
        except EndOfPacketError:
            pass

    def test_read_some_bits(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72'
        readed_bits = ""
        for i in range(3):
            bits_in_byte = ""
            for j in range(8):
                bits_in_byte += str(data_reader.read_bit())
            readed_bits += bits_in_byte[::-1]

        self.assertEqual(readed_bits, "011101100110111101110010")

    def test_read_some_extra_bits(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        try:
            data_reader._current_packet = b'\x76\x6f\x72'
            for i in range(4):
                for j in range(8):
                    data_reader.read_bit()
        except EndOfPacketError:
            pass

    def test_read_bits_for_unsigned_int(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x32\x56'
        self.assertEqual(data_reader.read_bits_for_int(1), 0)
        self.assertEqual(data_reader.read_bits_for_int(5), 25)
        self.assertEqual(data_reader.read_bits_for_int(9), 344)

    def test_read_bits_for_signed_int(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x32\x56'
        self.assertEqual(
            data_reader.read_bits_for_int(2, signed=True), -2)
        self.assertEqual(
            data_reader.read_bits_for_int(8, signed=True), -116)
        self.assertEqual(
            data_reader.read_bits_for_int(5, signed=True), -11)


class HelperFunctionsTests(unittest.TestCase):
    def test_ilog(self):
        self.assertEqual(ilog(0), 0)
        self.assertEqual(ilog(1), 1)
        self.assertEqual(ilog(-1111), 0)
        self.assertEqual(ilog(7), 3)

    def test_lookup1_values(self):
        self.assertEqual(lookup1_values(50, 3), 3)
        self.assertEqual(lookup1_values(1, 3), 1)

    def test_float32_unpack(self):
        assert float32_unpack(0x60A03250) == (12880 * pow(2, -15))
        assert float32_unpack(0xE0A03250) == -(12880 * pow(2, -15))


class PacketsProcessorTests(unittest.TestCase):
    def test_process_headers(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor.process_headers()

    def test_ident_header_processing(self):
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_streams = []
        packets_processor.logical_streams += \
            [PacketsProcessor.LogicalStream(0)]
        packets_processor._process_identification_header()

# 0000000  1  1011  1000
# 00000000000000000000000000000000
# 00000000000001110101111000111000
# 00000000000000000000000000000000
# 00000000000000001010110001000100  00000010
# 00000000000000000000000000000000
# 01110011  01101001  01100010  01110010  01101111  01110110
# 0000_0001 <- start

        logical_stream = packets_processor.logical_streams[0]
        assert logical_stream.audio_channels == 2
        assert logical_stream.audio_sample_rate == 44100
        assert logical_stream.bitrate_maximum == 0
        assert logical_stream.bitrate_nominal == 482872
        assert logical_stream.bitrate_minimum == 0
        assert logical_stream.blocksize_0 == 8
        assert logical_stream.blocksize_1 == 11


if __name__ == '__main__':
    unittest.main()
