from unittest import TestCase
from os import path as os_path
from typing import List

import tests.__init__  # Without this anytask won't see tests
from vorbis.decoders import *


PATH_ORDINARY_TEST_1 = os_path.join(
    os_path.dirname(os_path.abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')


def hex_str_to_bin_str(hex_str: str):
    """Hex string must be in format: '00 00 00 00'."""
    bin_values: List[str] = [
        bin(int(item, 16))[2:].zfill(8) for item in hex_str.split(' ')]

    return ' '.join([item[:4] + ' ' + item[4:] for item in bin_values])


# noinspection PyMethodMayBeStatic
class CodebookDecodingTests(TestCase):
    def test_codebook_sync_pattern_check(self):
        codebook_decoder = CodebookDecoder(DataReader(data=b'\x42\x43\x56'))

        codebook_decoder._check_codebook_sync_pattern()

    def test_read_codebook_1(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)
        codebook_decoder = CodebookDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8
        codebook_decoder.read_codebook()

        # test_1.ogg, codebook 1
        #                                                    05
        # 76 6F 72 62 | 69 73 2B 42 | 43 56 01 00 | 08 00 00 00
        # 31 4C 20 C5 | 80 D0 90 55 | 00 00 10 00 | 00 60 24 29
        # 0E 93 66 49 | 29 A5 94 A1 | 28 79 98 94 | 48 49 29 A5
        #
        # 05
        # 76 6F 72 62 . 69 73
        # 2B
        # 42 43 56
        # 01 00
        # 08 00 00
        # [bitstream starts]
        # 00 31 4C 20 C5 80 D0 90 55 00 00 10 00 00 60 24 29 0E 93 66 49 29 A5
        # 94 A1 28 79 98 94 48 49 29 A5
        #
        #
        #
        #
        #
        # Packet type. It's setup header packet
        # 05
        #
        # Header sync pattern, 'vorbis'
        # 76 6F 72 62 . 69 73
        #
        # Amount of codebooks. (Add one)
        # HEX: 2B
        # DEC: 43 (+ 1)
        #
        # Codebook sync pattern, 'BCV'
        # 42 43 56
        #
        # codebook_dimensions
        # HEX: 01 00
        # DEC: 1
        #
        # codebook_entries
        # HEX: 08 00 00
        # DEC: 8
        #
        #
        #
        #
        #
        #

        assert codebook_decoder._codebook_dimensions == 1
        assert codebook_decoder._codebook_entries == 8
        assert codebook_decoder._ordered == 0
        assert codebook_decoder._codebook_lookup_type == 0

        self.assertEqual(
            codebook_decoder._codebook_codewords_lengths,
            [1, 3, 4, 7, 2, 5, 6, 7])
        self.assertEqual(
            codebook_decoder._codebook_codewords,
            ['0', '100', '1010', '1011000',
             '11', '10111', '101101', '1011001'])

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


class HuffmanTests(TestCase):
    _codebook_decoder: CodebookDecoder = CodebookDecoder(DataReader())

    def test_1_Huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [
            -1, 2, 4, 4, 4, 4, 2, 3, 3]
        self._codebook_decoder._codebook_entries = 9

        self._test_huffman([
            '', '00', '0100', '0101', '0110', '0111', '10', '110', '111'])

    def test_2_Huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [
            1, 3, 4, 7, 2, 5, 6, 7]
        self._codebook_decoder._codebook_entries = 8

        self._test_huffman([
            '0', '100', '1010', '1011000', '11', '10111', '101101', '1011001'])

    def test_long_Huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [
            2, 5, 5, 4,
            5, 4, 5, 4,
            5, 5, 5, 5,
            5, 5, 6, 5,
            6, 5, 6, 5,
            7, 6, 7, 6,
            7, 6, 8, 6,
            9, 7, 9, 7]
        self._codebook_decoder._codebook_entries = 32

        self._test_huffman([
            '00', '01000', '01001', '0101',
            '01100', '0111', '01101', '1000',
            '10010', '10011', '10100', '10101',
            '10110', '10111', '110000', '11001',
            '110001', '11010', '110110', '11100',
            '1101110', '111010', '1101111', '111011',
            '1111000', '111101', '11110010', '111110',
            '111100110', '1111110', '111100111', '1111111'])

    def test_two_entries_Huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [1, 1]
        self._codebook_decoder._codebook_entries = 2

        self._test_huffman(['0', '1'])

    def _test_huffman(self, result_codewords: List[str]):
        self.assertEqual(
            self._codebook_decoder._huffman_decode_bfc(),
            result_codewords)

        self.assertEqual(
            self._codebook_decoder._huffman_decode(),
            result_codewords)

    _EXTREMELY_BIG_HUFFMAN: List[str] = [
        '0', '10000', '1000100', '100010100000000000000', '10010', '10001011',
        '100010101', '100010100000000000001', '1000101001', '100011000',
        '100010100001', '10001010000000000001', '10001010000000000010',
        '1000101000000001', '10001010000000000011', '10001010000000000100',
        '1010', '10001101', '100011001', '10001010000000000101', '100110',
        '10001110', '100011110', '10001010000000000110', '10001010001',
        '10001111100', '1000101000001', '10001010000000000111',
        '10001010000000001000', '100010100000001', '10001010000001000',
        '10001010000000001001', '100111000', '10001111101', '10001111110000',
        '10001010000000001010', '10011101', '1001110010', '100010100000011',
        '10001010000000001011', '10001111111', '1000111111001',
        '100011111100010', '10001010000000001100', '10001010000000001101',
        '10001010000000001110', '10001010000000001111',
        '10001010000001001000', '10001010000001001001',
        '10001010000001001010', '10001010000001001011',
        '10001010000001001100', '1000111111010', '10001010000001001101',
        '10001010000001001110', '10001010000001001111', '100010100000010100',
        '100010100000010101', '10001010000001011000', '10001010000001011001',
        '10001010000001011010', '10001010000001011011',
        '10001010000001011100', '10001010000001011101', '110', '101100',
        '10011110', '10001010000001011110', '101101', '1011100', '100111110',
        '10001010000001011111', '1001110011', '100111111', '101110100000',
        '10001111110001100000', '10001111110001100001',
        '10001111110001100010', '10001111110001100011',
        '10001111110001100100', '11100', '1011110', '101110101',
        '10001111110001100101', '111010', '111011', '101110110',
        '10001111110001100110', '1011101001', '101110111', '101110100001',
        '10001111110001100111', '10001111110001101000',
        '10001111110001101001', '10001111110001101010',
        '10001111110001101011', '10111110', '1011111100', '1000111111011',
        '10001111110001101100', '11110000', '101111111', '101110100010',
        '10001111110001101101', '10111111010', '1111000100', '101110100011',
        '10001111110001101110', '10001111110001101111',
        '10001111110001110000', '10001111110001110001',
        '10001111110001110010', '100011111100011101', '10001111110001110011',
        '10001111110001111000', '10001111110001111001', '101111110110000',
        '10111111011000100', '100011111100011111', '10001111110001111010',
        '101111110110001010', '10111111011000110', '101111110110001011',
        '10001111110001111011', '10111111011000111000',
        '10111111011000111001', '10111111011000111010',
        '10111111011000111011', '1111001', '1111000101', '101111110111',
        '10111111011000111100', '11110100', '111100011', '11110101000',
        '10111111011000111101', '10111111011001', '1011111101101',
        '11110101001000', '10111111011000111110', '10111111011000111111',
        '11110101001001000000', '11110101001001000001',
        '11110101001001000010', '111110', '111101011', '111101010011',
        '11110101001001000011', '1111011', '11111100', '11110101010',
        '11110101001001000100', '111101010110', '11111101000',
        '1111010100101', '11110101001001000101', '11110101001001000110',
        '11110101001001000111', '11110101001001001000',
        '11110101001001001001', '111111011', '11111101001', '111101010010011',
        '11110101001001001010', '11111110', '1111110101', '11110101011100',
        '11110101001001001011', '111111110000', '11111111001',
        '11110101011101', '11110101001001001100', '11110101001001001101',
        '11110101001001001110', '11110101001001001111',
        '11110101001001010000', '11110101001001010001',
        '11110101001001010010', '11110101001001010011',
        '11110101001001010100', '11110101001001010101',
        '11110101001001010110', '11110101001001010111',
        '11110101001001011000', '11110101001001011001',
        '11110101001001011010', '11110101001001011011',
        '11110101001001011100', '11110101001001011101',
        '11110101001001011110', '11110101001001011111',
        '11110101011110000000', '11111111010', '1111010101111001',
        '111101010111100001', '11110101011110000001', '111101010111101',
        '111101010111110', '11110101011110001', '11110101011110000010',
        '11110101011110000011', '11110101011111100', '11110101011111101000',
        '11110101011111101001', '11110101011111101010',
        '11110101011111101011', '11110101011111101100',
        '11110101011111101101', '111111111', '11111111000100',
        '1111010101111111', '11110101011111101110', '111111110110',
        '111111110111', '111111110001010', '11110101011111101111',
        '11111111000101100', '111111110001100', '111111110001011010',
        '11111111000101101100', '11111111000101101101',
        '11111111000101101110', '11111111000101101111',
        '11111111000101110000', '1111111100011010', '1111111100010111001',
        '111111110001011101', '11111111000101110001', '111111110001110',
        '1111111100011011', '11111111000101111000', '11111111000101111001',
        '11111111000111100', '11111111000111101', '11111111000101111010',
        '11111111000101111011', '11111111000101111100',
        '11111111000101111101', '11111111000101111110',
        '11111111000101111111', '11111111000111110000',
        '11111111000111110001', '11111111000111110010',
        '11111111000111110011', '11111111000111110100',
        '11111111000111110101', '11111111000111110110',
        '11111111000111110111', '11111111000111111000',
        '11111111000111111001', '11111111000111111010',
        '11111111000111111011', '11111111000111111100',
        '11111111000111111101', '11111111000111111110',
        '11111111000111111111']

    def test_extremely_big_huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [
            1, 5, 7, 21, 5, 8, 9, 21, 10, 9, 12, 20, 20, 16, 20, 20, 4, 8, 9,
            20, 6, 8, 9, 20, 11, 11, 13, 20, 20, 15, 17, 20, 9, 11, 14, 20,
            8, 10, 15, 20, 11, 13, 15, 20, 20, 20, 20, 20, 20, 20, 20, 20,
            13, 20, 20, 20, 18, 18, 20, 20, 20, 20, 20, 20, 3, 6, 8, 20, 6,
            7, 9, 20, 10, 9, 12, 20, 20, 20, 20, 20, 5, 7, 9, 20, 6, 6, 9,
            20, 10, 9, 12, 20, 20, 20, 20, 20, 8, 10, 13, 20, 8, 9, 12, 20,
            11, 10, 12, 20, 20, 20, 20, 20, 18, 20, 20, 20, 15, 17, 18, 20,
            18, 17, 18, 20, 20, 20, 20, 20, 7, 10, 12, 20, 8, 9, 11, 20, 14,
            13, 14, 20, 20, 20, 20, 20, 6, 9, 12, 20, 7, 8, 11, 20, 12, 11,
            13, 20, 20, 20, 20, 20, 9, 11, 15, 20, 8, 10, 14, 20, 12, 11,
            14, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
            20, 20, 20, 20, 20, 20, 11, 16, 18, 20, 15, 15, 17, 20, 20, 17,
            20, 20, 20, 20, 20, 20, 9, 14, 16, 20, 12, 12, 15, 20, 17, 15,
            18, 20, 20, 20, 20, 20, 16, 19, 18, 20, 15, 16, 20, 20, 17, 17,
            20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
            20, 20, 20, 20, 20, 20]
        self._codebook_decoder._codebook_entries = 256

        self.assertEqual(
            self._codebook_decoder._huffman_decode(),
            self._EXTREMELY_BIG_HUFFMAN)


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
