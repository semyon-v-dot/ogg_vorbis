import unittest
import sys
import os
import pathmagic
from vorbis.codebook import CodebookDecoder
from vorbis.vorbis_main import DataReader


PATH_ORDINARY_TEST_1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'ordinary_test_1.ogg')


class CodebookDecodingTests(unittest.TestCase):
    def test_codebook_sync_pattern_check(self):
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
        RBF = codebook_decoder.read_codebook  # RBF -> Read Book Function

# ... 0000  0_0110  0_0101  0_0100
# 0_0001  0_0110  0_0011  0_0010  0_0000  0  0  0000_0000_0000_0000_0000_1000
# 0000_0000_0000_0001  0101_0110  0100_0011  0100_0010 <- beginning here

        RBF()
        self.assertEqual(RBF.codebook_dimensions, 1)
        self.assertEqual(RBF.codebook_entries, 8)
        self.assertEqual(RBF.ordered, 0)
        self.assertEqual(RBF.codebook_codeword_lengths,
                         [1, 3, 4, 7, 2, 5, 6, 7])
        # self.assertEqual(RBF.codebook_codewords,
        #                  ['0', '100', '1010', '1011000',
        #                   '11', '10111', '101101', '1011001'])
        self.assertEqual(RBF.codebook_lookup_type, 0)

    def test_read_codebook_2(self):
        data_reader = DataReader(PATH_ORDINARY_TEST_1)
        codebook_decoder = CodebookDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 208
        RBF = codebook_decoder.read_codebook  # RBF -> Read Book Function

# ... 0000  0_0110
# 0_1000  0_0110  0_1000  0_0101  0_0111  0_0101  0_0110  0_0101  0_0110
# 0_0101  0_0110  0_0100  0_0101  0_0100  0_0101  0_0100  0_0101  0_0100
# 0_0100  0_0100  0_0100  0_0100  0_0100  0_0011  0_0100  0_0011  0_0100
# 0_0011  0_0100  0_0100  0_0001  0  0  0000_0000_0000_0000_0010_0000
# 0000_0000_0000_0001  0101_0110  0100_0011  0100_0010 <- beginning here

        RBF()
        self.assertEqual(RBF.codebook_dimensions, 1)
        self.assertEqual(RBF.codebook_entries, 32)
        self.assertEqual(RBF.ordered, 0)
        self.assertEqual(len(RBF.codebook_codeword_lengths),
                         RBF.codebook_entries)
        self.assertEqual(RBF.codebook_codeword_lengths,
                         [2, 5, 5, 4,
                          5, 4, 5, 4, 5, 5, 5, 5, 5,
                          5, 6, 5, 6, 5, 6, 5, 7, 6,
                          7, 6, 7, 6, 8, 6, 9, 7, 9,
                          7])
        # self.assertEqual(RBF.codebook_codewords,
        #                  ['00', '01000', '01001', '0101', '01100', '0111',
        #                   '01101', '1000', '10010', '10011', '10100',
        #                   '10101', '10110', '10111', '110000', '11001',
        #                   '110001', '11010', '110110', '11100', '1101110',
        #                   '111010', '1101111', '111011', '1111000',
        #                   '111101', '11110010', '111110', '111100110',
        #                   '1111110', '111100111', '1111111'])
        self.assertEqual(RBF.codebook_lookup_type, 0)


class HuffmanTests(unittest.TestCase):  # test not only bfc
    def test_ordinary_1_Huffman_tree_decode(self):
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codeword_lengths = [-1, 2, 4, 4, 4, 4, 2, 3, 3]
        codebook_codewords = ['', '00', '0100', '0101',
                              '0110', '0111', '10', '110', '111']
        assert codebook_decoder.\
            _Huffman_tree_decode_bfc(9, codebook_codeword_lengths) == \
            codebook_codewords

    def test_ordinary_2_Huffman_tree_decode(self):
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codeword_lengths = [1, 3, 4, 7, 2, 5, 6, 7]
        codebook_codewords = ['0', '100', '1010', '1011000',
                              '11', '10111', '101101', '1011001']
        assert codebook_decoder.\
            _Huffman_tree_decode_bfc(8, codebook_codeword_lengths) == \
            codebook_codewords

    def test_long_Huffman_tree_decode(self):
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codeword_lengths = [2, 5, 5, 4,
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
            _Huffman_tree_decode_bfc(32, codebook_codeword_lengths) == \
            codebook_codewords

    def test_two_entries_Huffman_tree_decode(self):
        codebook_decoder = CodebookDecoder(DataReader(PATH_ORDINARY_TEST_1))

        codebook_codeword_lengths = [1, 1]
        codebook_codewords = ['0', '1']
        assert codebook_decoder.\
            _Huffman_tree_decode_bfc(2, codebook_codeword_lengths) == \
            codebook_codewords


if __name__ == '__main__':
    unittest.main()
