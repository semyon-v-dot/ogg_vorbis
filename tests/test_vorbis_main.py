from unittest import TestCase
from os import path as os_path

import tests.__init__  # Without this anytask won't see tests
from vorbis.vorbis_main import (
    DataReader, EndOfPacketException, PacketsProcessor, CodebookDecoder)
from vorbis.helper_funcs import (
    ilog, lookup1_values, float32_unpack, bit_reverse)


PATH_ORDINARY_TEST_1 = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')


class DataReaderTests(TestCase):
    def test_read_some_bytes(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72\x62\x69\x73'
        read_bytes = b''
        for i in range(6):
            read_bytes += data_reader.read_byte()

        self.assertEqual(read_bytes, b'\x76\x6f\x72\x62\x69\x73')

    @staticmethod
    def test_read_some_extra_bytes():
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72\x62\x69\x73'
        try:
            for i in range(7):
                data_reader.read_byte()
        except EndOfPacketException:
            pass

    def test_read_some_bits(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        data_reader._current_packet = b'\x76\x6f\x72'
        read_bits = ""
        for i in range(3):
            bits_in_byte = ""
            for j in range(8):
                bits_in_byte += str(data_reader.read_bit())
            read_bits += bits_in_byte[::-1]

        self.assertEqual(read_bits, "011101100110111101110010")

    @staticmethod
    def test_read_some_extra_bits():
        data_reader = DataReader(PATH_ORDINARY_TEST_1)

        try:
            data_reader._current_packet = b'\x76\x6f\x72'
            for i in range(4):
                for j in range(8):
                    data_reader.read_bit()
        except EndOfPacketException:
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


class HelperFunctionsTests(TestCase):
    def test_ilog(self):
        self.assertEqual(ilog(0), 0)
        self.assertEqual(ilog(1), 1)
        self.assertEqual(ilog(-1111), 0)
        self.assertEqual(ilog(7), 3)

    def test_lookup1_values(self):
        self.assertEqual(lookup1_values(50, 3), 3)
        self.assertEqual(lookup1_values(1, 3), 1)

    @staticmethod
    def test_float32_unpack():
        assert float32_unpack(0x60A03250) == (12880 * pow(2, -15))
        assert float32_unpack(0xE0A03250) == -(12880 * pow(2, -15))

    @staticmethod
    def test_bit_reverse():
        assert bit_reverse(1879048192) == 14
        assert bit_reverse(64424509440) == 0
        assert bit_reverse(48) == 201326592


class PacketsProcessorTests(TestCase):
    @staticmethod
    def test_process_headers():
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor.process_headers()

    @staticmethod
    def test_ident_header_processing():
        packets_processor = PacketsProcessor(PATH_ORDINARY_TEST_1)

        packets_processor._data_reader.read_packet()
        packets_processor._data_reader.byte_pointer = 1
        packets_processor.logical_streams = []
        packets_processor.logical_streams.append(
            PacketsProcessor.LogicalStream(0))
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


class CodebookDecodingTests(TestCase):
    @staticmethod
    def test_codebook_sync_pattern_check():
        data_reader = DataReader(PATH_ORDINARY_TEST_1)
        codebook_decoder = CodebookDecoder(data_reader)

        data_reader._current_packet = b'\x42\x43\x56'
        codebook_decoder._check_codebook_sync_pattern()

    def test_read_codebook_1(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)
        codebook_decoder = CodebookDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8
        rbf = codebook_decoder.read_codebook  # rbf -> Read Book Function

# ... 0000  0_0110  0_0101  0_0100
# 0_0001  0_0110  0_0011  0_0010  0_0000  0  0  0000_0000_0000_0000_0000_1000
# 0000_0000_0000_0001  0101_0110  0100_0011  0100_0010 <- beginning here

        rbf()
        self.assertEqual(rbf.codebook_dimensions, 1)
        self.assertEqual(rbf.codebook_entries, 8)
        self.assertEqual(rbf.ordered, 0)
        self.assertEqual(rbf.codebook_codewords_lengths,
                         [1, 3, 4, 7, 2, 5, 6, 7])
        # self.assertEqual(rbf.codebook_codewords,
        #                  ['0', '100', '1010', '1011000',
        #                   '11', '10111', '101101', '1011001'])
        self.assertEqual(rbf.codebook_lookup_type, 0)

    def test_read_codebook_2(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)
        codebook_decoder = CodebookDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 208
        rbf = codebook_decoder.read_codebook  # rbf -> Read Book Function

# ... 0000  0_0110
# 0_1000  0_0110  0_1000  0_0101  0_0111  0_0101  0_0110  0_0101  0_0110
# 0_0101  0_0110  0_0100  0_0101  0_0100  0_0101  0_0100  0_0101  0_0100
# 0_0100  0_0100  0_0100  0_0100  0_0100  0_0011  0_0100  0_0011  0_0100
# 0_0011  0_0100  0_0100  0_0001  0  0  0000_0000_0000_0000_0010_0000
# 0000_0000_0000_0001  0101_0110  0100_0011  0100_0010 <- beginning here

        rbf()
        self.assertEqual(rbf.codebook_dimensions, 1)
        self.assertEqual(rbf.codebook_entries, 32)
        self.assertEqual(rbf.ordered, 0)
        self.assertEqual(len(rbf.codebook_codewords_lengths),
                         rbf.codebook_entries)
        self.assertEqual(rbf.codebook_codewords_lengths,
                         [2, 5, 5, 4,
                          5, 4, 5, 4, 5, 5, 5, 5, 5,
                          5, 6, 5, 6, 5, 6, 5, 7, 6,
                          7, 6, 7, 6, 8, 6, 9, 7, 9,
                          7])
        # self.assertEqual(rbf.codebook_codewords,
        #                  ['00', '01000', '01001', '0101', '01100', '0111',
        #                   '01101', '1000', '10010', '10011', '10100',
        #                   '10101', '10110', '10111', '110000', '11001',
        #                   '110001', '11010', '110110', '11100', '1101110',
        #                   '111010', '1101111', '111011', '1111000',
        #                   '111101', '11110010', '111110', '111100110',
        #                   '1111110', '111100111', '1111111'])
        self.assertEqual(rbf.codebook_lookup_type, 0)


class HuffmanTests(TestCase):  # test not only bfc
    @staticmethod
    def test_1_Huffman_decode():
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codewords_lengths = [-1, 2, 4, 4, 4, 4, 2, 3, 3]
        codebook_codewords = ['', '00', '0100', '0101',
                              '0110', '0111', '10', '110', '111']
        assert codebook_decoder.\
            _huffman_decode_bfc(9, codebook_codewords_lengths) == \
               codebook_codewords

    @staticmethod
    def test_2_Huffman_decode():
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codewords_lengths = [1, 3, 4, 7, 2, 5, 6, 7]
        codebook_codewords = ['0', '100', '1010', '1011000',
                              '11', '10111', '101101', '1011001']
        assert codebook_decoder.\
            _huffman_decode_bfc(8, codebook_codewords_lengths) == \
               codebook_codewords

    @staticmethod
    def test_long_Huffman_decode():
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codewords_lengths = [2, 5, 5, 4,
                                      5, 4, 5, 4, 5, 5, 5, 5, 5,
                                      5, 6, 5, 6, 5, 6, 5, 7, 6,
                                      7, 6, 7, 6, 8, 6, 9, 7, 9,
                                      7]
        codebook_codewords = ['00', '01000', '01001', '0101', '01100', '0111',
                              '01101', '1000', '10010', '10011', '10100',
                              '10101', '10110', '10111', '110000', '11001',
                              '110001', '11010', '110110', '11100', '1101110',
                              '111010', '1101111', '111011', '1111000',
                              '111101', '11110010', '111110', '111100110',
                              '1111110', '111100111', '1111111']
        assert codebook_decoder.\
            _huffman_decode_bfc(32, codebook_codewords_lengths) == \
               codebook_codewords

    @staticmethod
    def test_two_entries_Huffman_decode():
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codewords_lengths = [1, 1]
        codebook_codewords = ['0', '1']
        assert codebook_decoder.\
            _huffman_decode_bfc(2, codebook_codewords_lengths) == \
               codebook_codewords
