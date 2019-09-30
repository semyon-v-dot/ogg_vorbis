from unittest import TestCase, main as unittest_main
from os import pardir as os_pardir
from os.path import (
    join as os_path_join,
    dirname as os_path_dirname,
    abspath as os_path_abspath)
from typing import List, Tuple
from sys import path as sys_path

sys_path.append(os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    os_pardir))

from vorbis.decoders import (
    DataReader,
    SetupHeaderDecoder,
    EndOfPacketException)
from vorbis.helper_funcs import float32_unpack


PATH_TEST_1 = os_path_join(
    os_path_dirname(os_path_abspath(__file__)),
    'test_audiofiles',
    'test_1.ogg')


def hex_str_to_bin_str(hex_str: str):
    """Hex string must be in format: '00 00 00 00'."""
    bin_values: List[str] = [
        bin(int(item, 16))[2:].zfill(8) for item in hex_str.split(' ')]

    return ' '.join([item[:4] + '_' + item[4:] for item in bin_values])


class DataReaderTests(TestCase):
    def test_read_some_bytes(self):
        data_reader = DataReader(data=b'\x76\x6f\x72\x62\x69\x73')

        self.assertEqual(
            data_reader.read_bytes(6),
            b'\x76\x6f\x72\x62\x69\x73')

    def test_read_some_extra_bytes(self):
        data_reader = DataReader(data=b'\x76\x6f\x72\x62\x69\x73')

        with self.assertRaises(EndOfPacketException):
            data_reader.read_bytes(7)

    def test_read_some_bits(self):
        # 92 E4 -> 1001_0010 1110_0100
        data_reader = DataReader(data=b'\x92\xE4')

        self.assertEqual(
            data_reader._read_bits(2 * 8),
            "1110010010010010")

    def test_read_some_extra_bits(self):
        data_reader = DataReader(data=b'\x76\x6f\x72')

        with self.assertRaises(EndOfPacketException):
            data_reader._read_bits(8 * 3 + 1)

    def test_read_bits_for_unsigned_int(self):
        data_reader = DataReader(PATH_TEST_1)

        data_reader._current_packet = b'\x32\x56'
        self.assertEqual(data_reader.read_bits_for_int(1), 0)
        self.assertEqual(data_reader.read_bits_for_int(5), 25)
        self.assertEqual(data_reader.read_bits_for_int(9), 344)

    def test_read_bits_for_signed_int(self):
        data_reader = DataReader(data=b'\x32\x56')

        self.assertEqual(
            data_reader.read_bits_for_int(2, signed=True), -2)
        self.assertEqual(
            data_reader.read_bits_for_int(8, signed=True), -116)
        self.assertEqual(
            data_reader.read_bits_for_int(5, signed=True), -11)


class SetupHeaderDecodingTests(TestCase):
    def test_codewords_reading_not_ordered_and_not_sparse(self):
        data_reader = DataReader(PATH_TEST_1)
        codebook_decoder = SetupHeaderDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8
        codebook_decoder.read_codebook()

        # test_1.ogg, codebook 1
        #                                                    05
        # 76 6F 72 62 | 69 73 2B 42 | 43 56 01 00 | 08 00 00 00
        # 31 4C 20 C5 | 80 D0 90 55 | 00 00 10 00 | 00 60 24 29
        # 0E 93 66 49 | 29 A5 94 A1 | 28 79 98 94 | 48 49 29 A5 [...]
        #
        # 05
        # 76 6F 72 62 . 69 73
        # 2B
        # 42 43 56
        # 01 00
        # 08 00 00
        # [bitstream starts]
        # 00 31 4C 20 | 0000_0000 0011_0001 0100_1100 0010_0000
        # C5 80 D0 90 | 1100_0101 1000_0000 1101_0000 1001_0000
        # 55 00 00 10 | 0101_0101 0000_0000 0000_0000 0001_0000
        # 00 00 60 24 | 0000_0000 0000_0000 0110_0000 0010_0100
        # 29 0E 93 66 | 0010_1001 0000_1110 1001_0011 0110_0110
        # 49 29 A5 94 | 0100_1001 0010_1001 1010_0101 1001_0100
        # A1 28 79 98 | 1010_0001 0010_1000 0111_1001 1001_1000
        # 94 48 49 29 | 1001_0100 0100_1000 0100_1001 0010_1001
        # A5 [...]    | 1010_0101
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
        # [bitstream starts]
        # (NOTE: '()' AND '|' for moved bits. '_' for readability)
        #
        # (0) [0000_0] -> length_1 [0] -> sparse [0] -> ordered
        # (0011) [0001|0] -> length_2
        # (01) [0011_0] -> length_4 [0|0011] -> length_3
        # [0010_0] -> length_6 [000|01] -> length_5
        # (110) [0010_1] -> length_7
        # [...] [0000] -> codebook_lookup_type [00|110] -> length_8

        assert codebook_decoder._codebook_dimensions == 1
        assert codebook_decoder._codebook_entries == 8
        assert codebook_decoder._ordered == 0
        assert codebook_decoder._sparse == 0
        assert codebook_decoder._codebook_lookup_type == 0

        self.assertEqual(
            codebook_decoder._codebook_codewords_lengths,
            [1, 3, 4, 7, 2, 5, 6, 7])
        self.assertEqual(
            codebook_decoder._codebook_codewords,
            ['0', '100', '1010', '1011000', '11', '10111', '101101',
             '1011001'])

    def test_codewords_reading_not_ordered_and_sparse(self):
        data_reader = DataReader(PATH_TEST_1)
        codebook_decoder = SetupHeaderDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        for i in range(29):
            codebook_decoder.read_codebook()

        self.assertEqual(
            codebook_decoder.last_read_codebook_position,
            (120230, 0))

        # [bitstream]
        #       42 43 |                     0100_0010 0100_0011
        # 56 04 00 51 | 0101_0110 0000_0100 0000_0000 0101_0001
        # 00 00 06 49 | 0000_0000 0000_0000 0000_0110 0100_1001
        # 22 49 24 C9 | 0010_0010 0100_1001 0010_0100 1100_1001 ...
        #
        # [bitstream]
        # [0100_0010] -> B
        # [0100_0011] -> C
        # [0101_0110] -> V
        # (0000_0100)
        # [0000_0000|0000_0100] -> codebook_dimensions
        # (0101_0001)
        # (0000_0000|0101_0001)
        # [0000_0000|0000_0000||0101_0001] -> codebook_entries
        # [0000_0] -> length_1 [1] -> flag_1 [1] -> sparse [0] -> ordered
        # (0) [1] -> flag_3 [00_100] -> length_2 [1] -> flag_2
        # (00) [1] -> flag_5 [0] -> flag_4 [0010|0] -> length_3
        # (0100) [1] -> flag_6 [001|00] -> length_5
        # [0010_0]-> length_8 [1]-> flag_8 [0]-> flag_7 [0|0100]-> length_6
        # ...

        self.assertEqual(codebook_decoder._codebook_dimensions, 4)
        self.assertEqual(codebook_decoder._codebook_entries, 81)
        self.assertEqual(codebook_decoder._ordered, False)
        self.assertEqual(codebook_decoder._sparse, True)

        self.assertEqual(
            len(codebook_decoder._codebook_codewords_lengths), 81)
        self.assertEqual(
            codebook_decoder._codebook_codewords_lengths[:8],
            [1, 5, 5, None, 5, 5, None, 5])

        self.assertEqual(
            len(codebook_decoder._codebook_codewords), 81)
        self.assertEqual(
            codebook_decoder._codebook_codewords[:8],
            ['0', '10000', '10001', '', '10010', '10011', '', '10100'])

    def test_codewords_lengths_reading_ordered(self):
        data_reader = DataReader(PATH_TEST_1)
        codebook_decoder = SetupHeaderDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        for i in range(43):
            codebook_decoder.read_codebook()

        self.assertEqual(
            codebook_decoder.last_read_codebook_position, (122333, 7))

        # [bitstream]
        #    48 A1 21 |           0100_1000 1010_0001 0010_0001
        # AB 00 80 18 | 1010_1011 0000_0000 1000_0000 0001_1000
        # 00 80 21 00 | 0000_0000 1000_0000 0010_0001 0000_0000
        # 84 62 B2 01 | 1000_0100 0110_0010 1011_0010 0000_0001
        # 00 80 09 0E | 0000_0000 1000_0000 0000_1001 0000_1110 ...
        #
        # [bitstream]
        # (0) [100_1000]-> previous codebook
        # (1) [010_0001|0]-> B
        # (0) [010_0001|1]-> C
        # (1) [010_1011|0]-> V
        # (0000_0000|1)
        # (1) [000_0000|0000_0000||1]-> codebook_dimensions
        # (0001_1000|1)
        # (0000_0000|0001_1000||1)
        # [1]-> ordered [000_0000|0000_0000||0001_1000|||1]-> codebook_entries
        # (001) [0_0001]-> length_1
        # (0000_0) [000|001]-> number_1
        # (1) [000_010]-> number_3 [0|0000_0]-> number_2
        # (011) [0_0010|1]-> number_4
        # 1011_0 [010|011]-> number_5

        self.assertEqual(codebook_decoder._codebook_dimensions, 1)
        self.assertEqual(codebook_decoder._codebook_entries, 0b1_1000_1)
        self.assertEqual(codebook_decoder._ordered, True)

        self.assertEqual(
            len(codebook_decoder._codebook_codewords_lengths), 0b1_10001)
        self.assertEqual(
            codebook_decoder._codebook_codewords_lengths[:27],
            [2, 4, 4] + [5] * 5 + [6] * 19)

    # There is no need to test lookup type 2 values reading because the only
    # difference is calculation of [_codebook_lookup_values]. And this
    # calculation takes place in 'lookup1_values' function that is tested in
    # 'test_helper_funcs.py'
    def test_lookup_values_reading_type_1(self):
        data_reader = DataReader(PATH_TEST_1)
        codebook_decoder = SetupHeaderDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        for i in range(29):
            codebook_decoder.read_codebook()

        self.assertEqual(
            codebook_decoder.last_read_codebook_position,
            (120230, 0))

        # Global position: (120279, 0)
        #
        # [bitstream]
        #          01 |                               0000_0001
        # 00 00 01 0E | 0000_0000 0000_0000 0000_0001 0000_1110
        # 00 00 01 16 | 0000_0000 0000_0000 0000_0001 0001_0110
        # 42 A1 21 2B | 0100_0010 1010_0001 0010_0001 0010_1011 ...
        #
        # [bitstream]
        # (0000) [0001]-> codebook_lookup_type
        # (0000_0000|0000)
        # (0000_0000|0000_0000||0000)
        # (0000_0001|0000_0000||0000_0000|||0000)
        # (0000) [1110|0000_0001||0000_0000|||0000_0000||||0000]->
        # # -> codebook_minimum_value
        # (0000_0000|0000)
        # (0000_0000|0000_0000||0000)
        # (0000_0001|0000_0000||0000_0000|||0000)
        # (0001) [0110|0000_0001||0000_0000|||0000_0000||||0000]->
        # # -> codebook_delta_value
        # (010) [0_0]-> v2 [01]-> v1 [0]-> codebook_sequence_p | [0001]->
        # codebook_value_bits
        # 1010_0001|0 [10]-> v3

        self.assertEqual(codebook_decoder._codebook_minimum_value, -1.0)
        self.assertEqual(
            codebook_decoder._codebook_delta_value,
            float32_unpack(0b01100000000100000000000000000000))

        self.assertEqual(codebook_decoder._codebook_value_bits, 2)
        self.assertEqual(codebook_decoder._codebook_sequence_p, False)

        self.assertEqual(codebook_decoder._codebook_lookup_values, 3)

        self.assertEqual(
            len(codebook_decoder._codebook_multiplicands),
            codebook_decoder._codebook_lookup_values)
        self.assertEqual(
            codebook_decoder._codebook_multiplicands,
            [1, 0, 2])

    def test_vq_table_unpacking_lookup_type_1(self):
        codebook_decoder = SetupHeaderDecoder(DataReader())

        codebook_decoder._codebook_multiplicands = [1, 0, 2]

        codebook_decoder._codebook_minimum_value = -1.0
        codebook_decoder._codebook_delta_value = 1.0

        codebook_decoder._codebook_sequence_p = False
        codebook_decoder._codebook_lookup_type = 1
        codebook_decoder._codebook_entries = 81
        codebook_decoder._codebook_dimensions = 4
        codebook_decoder._codebook_lookup_values = 3

        result_vq_lookup_table: List[List[float]] = (
            codebook_decoder._vq_lookup_table_unpack())

        self.assertEqual(len(result_vq_lookup_table), 81)

        self.assertEqual(result_vq_lookup_table[0], [0.0, 0.0, 0.0, 0.0])
        self.assertEqual(result_vq_lookup_table[1], [-1.0, 0.0, 0.0, 0.0])
        self.assertEqual(result_vq_lookup_table[2], [1.0, 0.0, 0.0, 0.0])

        self.assertEqual(result_vq_lookup_table[3], [0.0, -1.0, 0.0, 0.0])
        self.assertEqual(result_vq_lookup_table[4], [-1.0, -1.0, 0.0, 0.0])
        self.assertEqual(result_vq_lookup_table[5], [1.0, -1.0, 0.0, 0.0])

    # Optimize: NO TEST DATA
    def test_vq_table_unpacking_lookup_type_2(self):
        pass

    # Optimize: NO TEST DATA
    def test_vq_table_unpacking_sequence_p_is_true(self):
        pass

    def test_floor_1_decoding(self):
        data_reader = DataReader(PATH_TEST_1)
        codebook_decoder = SetupHeaderDecoder(data_reader)

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        for i in range(44):
            codebook_decoder.read_codebook()

        for i in range(data_reader.read_bits_for_int(6) + 1):
            placeholder = data_reader.read_bits_for_int(16)

            self.assertEqual(placeholder, 0)

        #       80 20 |                     1000_0000 0010_0000
        # 00 C0 40 84 | 0000_0000 1100_0000 0100_0000 1000_0100
        # CC 04 02 05 | 1100_1100 0000_0100 0000_0010 0000_0101
        # 50 60 20 03 | 0101_0000 0110_0000 0010_0000 0000_0011
        # 00 0E 10 12 | 0000_0000 0000_1110 0001_0000 0001_0010
        # A4 00 80 C2 | 1010_0100 0000_0000 1000_0000 1100_0010
        # 02 43 C7 70 | 0000_0010 0100_0011 1100_0111 0111_0000
        # 11 10 90 4B | 0001_0001 0001_0000 1001_0000 0100_1011
        # C8 28 30 28 | 1100_1000 0010_1000 0011_0000 0010_1000
        # 1C 13 CE 49 | 0001_1100 0001_0011 1100_1110 0100_1001
        # A7 0D 00 40 | 1010_0111 0000_1101 0000_0000 0100_0000
        # 10 22 33 44 | 0001_0000 0010_0010 0011_0011 0100_0100
        # 22 62 31 48 | 0010_0010 0110_0010 0011_0001 0100_1000
        # 4C A8 06 8A | 0100_1100 1010_1000 0000_0110 1000_1010
        # 8A E9 00 60 | 1000_1010 1110_1001 0000_0000 0110_0000
        # 71 81 21 1F | 0111_0001 1000_0001 0010_0001 0001_1111
        #
        # [bitstream]
        # (1) [000_0000]-> previous things
        # (001) [0_0000|1]-> vorbis_floor_count
        # (0000_0000|001)
        # (110) [0_0000|0000_0000||001]-> vorbis_floor_types[0]
        # (01) [00_00]  [00|110]-> floor1_partitions
        # (10) [00_01] [00|01]-> floor1_partition_class_list second element
        # (11) [00_11] [00|10]
        # (0) [00]-> class_subclasses[0] [0_01]-> class_dimensions[0] [00|11]
        # (0) [000_0010|0]-> subclass_books[0][0]+1
        # (0000) [01]-> class_subclasses[1] [01|0]-> class_dimensions[1]
        # (0101) [0000|0000]-> class_masterbooks[1]
        # (0110) [0000|0101]-> subclass_books[1][0]
        # (0) [010]-> class_dimensions[2] [0000|0110]-> subclass_books[1][1]
        # (0000_001) [1|0]-> class_subclasses[2]
        # (0000_000) [0|0000_001]-> class_masterbooks[2]
        # (0000_111) [0|0000_000]-> subclass_books[2][0]
        # (0001_000) [0|0000_111]-> subclass_books[2][1]
        # (0001_001) [0|0001_000]-> subclass_books[2][2]
        # (1010_010)  [0|0001_001]-> subclass_books[2][3]
        # (0000_0000|10) [10]-> class_subclasses[3] [010]-> class_dimensions[3]
        # (1000_0000|00) [00_0000||10]-> class_masterbooks[3]
        # (11) [00_0010|10]-> s_bs[3][1] [00_0000||00]-> subclass_books[3][0]
        # (00) [00_0010|11]-> s_bs[3][2]
        # [01]-> floor1_multiplier [00_0011|00]-> s_bs[3][3]
        # (1100) [0111]-> rangebits
        # (0111_0) [000|1100]-> floor1_X_list[2]
        # 0001_00 [01|0111_0]-> floor1_X_list[3]

        # Floors count
        self.assertEqual(2, data_reader.read_bits_for_int(6) + 1)

        # First floor's type
        self.assertEqual(1, data_reader.read_bits_for_int(16))

        floors_decoder: SetupHeaderDecoder = SetupHeaderDecoder(data_reader)

        first_floor_data: SetupHeaderDecoder.FloorData = (
            floors_decoder._decode_floor_config_type_1(44))

        # floor1_partitions = 5

        self.assertEqual(
            [0, 1, 1, 2, 3, 3],
            first_floor_data.floor1_partition_class_list)

        # maximum_class = 3

        # iterate [i] over the range 0 ... [maximum_class]

        # i = 0
        self.assertEqual(2, first_floor_data.floor1_class_dimensions[0])
        self.assertEqual(0, first_floor_data.floor1_class_subclasses[0])
        self.assertEqual(None, first_floor_data.floor1_class_masterbooks[0])
        self.assertEqual(3, first_floor_data.floor1_subclass_books[0][0])

        # i = 1
        self.assertEqual(3, first_floor_data.floor1_class_dimensions[1])
        self.assertEqual(1, first_floor_data.floor1_class_subclasses[1])
        self.assertEqual(0, first_floor_data.floor1_class_masterbooks[1])
        self.assertEqual(4, first_floor_data.floor1_subclass_books[1][0])
        self.assertEqual(5, first_floor_data.floor1_subclass_books[1][1])

        # i = 2
        self.assertEqual(
            0b010 + 1, first_floor_data.floor1_class_dimensions[2])
        self.assertEqual(0b10, first_floor_data.floor1_class_subclasses[2])
        self.assertEqual(
            0b00000_001, first_floor_data.floor1_class_masterbooks[2])
        self.assertEqual(
            0b00000_000 - 1, first_floor_data.floor1_subclass_books[2][0])
        self.assertEqual(
            0b00000_111 - 1, first_floor_data.floor1_subclass_books[2][1])
        self.assertEqual(
            0b00001_000 - 1, first_floor_data.floor1_subclass_books[2][2])
        self.assertEqual(
            0b00001_001 - 1, first_floor_data.floor1_subclass_books[2][3])

        # i = 3
        self.assertEqual(
            0b010 + 1, first_floor_data.floor1_class_dimensions[3])
        self.assertEqual(0b10, first_floor_data.floor1_class_subclasses[3])
        self.assertEqual(
            0b00_000010, first_floor_data.floor1_class_masterbooks[3])
        self.assertEqual(
            0b00_000000 - 1, first_floor_data.floor1_subclass_books[3][0])
        self.assertEqual(
            0b00_001010 - 1, first_floor_data.floor1_subclass_books[3][1])
        self.assertEqual(
            0b00_001011 - 1, first_floor_data.floor1_subclass_books[3][2])
        self.assertEqual(
            0b00_001100 - 1, first_floor_data.floor1_subclass_books[3][3])

        # floor1_multiplier = 1 + 1 = 2
        rangebits: int = 0b0111  # = 7

        self.assertEqual(0, first_floor_data.floor1_x_list[0])
        self.assertEqual(2**rangebits, first_floor_data.floor1_x_list[1])

        # iterate [i] over the range 0 ... [floor1_partitions] - 1

        # i = 0

        # current_class_number = floor1_partition_class_list[0] = 2
        # floor1_class_dimensions[current_class_number] =
        #   floor1_class_dimensions[2] = 0b010 + 1 = 3

        # iterate [j] over the range 0 ...
        #   [(floor1_class_dimensions[current_class_number]) - 1] = 2

        self.assertEqual(0b0001100, first_floor_data.floor1_x_list[2])
        self.assertEqual(0b010111_0, first_floor_data.floor1_x_list[3])

    # WouldBeBetter: Test situation when [bitflag] is set
    def test_residue_decoding(self):
        """
        From docs:
        "Header decode for all three residue types is identical"
        """
        data_reader = DataReader(PATH_TEST_1)
        setup_header_decoder: SetupHeaderDecoder = (
            SetupHeaderDecoder(data_reader))

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        codebooks_configs: List[SetupHeaderDecoder.CodebookData] = []

        for i in range(44):
            codebooks_configs.append(setup_header_decoder.read_codebook())

        for i in range(data_reader.read_bits_for_int(6) + 1):
            placeholder = data_reader.read_bits_for_int(16)

            self.assertEqual(placeholder, 0)

        setup_header_decoder.read_floors(44)

        # Current global position: (122566, 5)
        #
        # -- -- 3A 10 |                     0011_1010 0001_0000
        # 00 00 00 00 | 0000_0000 0000_0000 0000_0000 0000_0000
        # 00 08 00 78 | 0000_0000 0000_1000 0000_0000 0111_1000
        # 00 00 48 36 | 0000_0000 0000_0000 0100_1000 0011_0110
        # 80 88 68 66 | 1000_0000 1000_1000 0110_1000 0110_0110
        # E6 38 3A 3C | 1110_0110 0011_1000 0011_1010 0011_1100
        #
        # [bitstream]
        # (001) (1_1010)-> previous things
        # (0001_0) [000|001]-> vorbis_residue_count
        # (0000_0000|0001_0)
        # (0000_0) [000|0000_0000||0001_0]-> vorbis_residue_types[0]
        # (0000_0000|0000_0)
        # (0000_0000|0000_0000||0000_0)
        # (0000_0) [000|0000_0000||0000_0000|||0000_0]-> residue_begin
        # (0000_1000|0000_0)
        # (0000_0000|0000_1000||0000_0)
        # (0111_1) [000|0000_0000||0000_1000|||0000_0]-> residue_end
        # (0000_0000|0111_1)
        # (0000_0000|0000_0000||0111_1)
        # (0100_1) [000|0000_0000||0000_0000|||0111_1]-> residue_partition_size
        # (0011_011) [0|0100_1]-> residue_classifications
        # (100) [0]-> bitflag [000]-> low_bits [0|0011_011]-> residue_classbook
        # (100) [0]-> bitflag [100]-> low_bits [0]-> bitflag | [100]-> low_bits
        # (011) [0]-> bitflag [100]-> low_bits [0]-> bitflag | [100]-> low_bits
        # [011] [0] [011] [0] | [011]
        # [111] [0] [011] [0]
        # (0011_100) [0]
        # (0011_101) [0|0011_100]-> residue_books[1][2]
        # 0011_110 [0|0011_101]-> residue_books[2][2]

        # [vorbis_residue_count] = 2

        residue_types: List[int]
        residue_configurations: List[SetupHeaderDecoder.ResidueData]

        (residue_types, residue_configurations) = (
            setup_header_decoder.read_residues(codebooks_configs))

        self.assertEqual(2, len(residue_types))
        self.assertEqual(2, len(residue_configurations))

        self.assertEqual(2, residue_types[0])

        self.assertEqual(0, residue_configurations[0].residue_begin)
        self.assertEqual(
            0b0000000_00000000_10000000_0,
            residue_configurations[0].residue_end)
        self.assertEqual(
            0b0000000_00000000_00000111_1 + 1,
            residue_configurations[0].residue_partition_size)
        self.assertEqual(
            0b00100_1 + 1,  # 10
            residue_configurations[0].residue_classifications)
        self.assertEqual(
            0b00011_011,
            residue_configurations[0].residue_classbook)

        high_bits: int
        low_bits: int

        # iterate [i] over the range 0 ... [residue_classifications] - 1

        # i = 0
        #
        high_bits = 0
        low_bits = 0
        # bitflag = 0
        self.assertEqual(
            high_bits * 8 + low_bits,
            residue_configurations[0].residue_cascade[0])

        # i = 1
        #
        high_bits = 0
        low_bits = 0b100
        # bitflag = 0
        self.assertEqual(
            high_bits * 8 + low_bits,
            residue_configurations[0].residue_cascade[1])

        self.assertEqual(
            0 * 8 + 0b100,
            residue_configurations[0].residue_cascade[2])

        # iterate [i] over the range 0 ... [residue_classifications] - 1

        # i = 0

        # iterate [j] over the range 0 ... 7

        self.assertEqual(
            [None, None, None, None, None, None, None, None],
            residue_configurations[0].residue_books[0])

        # i = 1

        self.assertEqual(
            [None, None, 0b00011_100, None, None, None, None, None],
            residue_configurations[0].residue_books[1])

        # i = 2

        self.assertEqual(
            [None, None, 0b00011_101, None, None, None, None, None],
            residue_configurations[0].residue_books[2])

    def test_mapping_decoding_second_flag_set(self):
        data_reader = DataReader(PATH_TEST_1)
        setup_header_decoder: SetupHeaderDecoder = (
            SetupHeaderDecoder(data_reader))

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        codebooks_configs: List[SetupHeaderDecoder.CodebookData] = []

        for i in range(44):
            codebooks_configs.append(setup_header_decoder.read_codebook())

        for i in range(data_reader.read_bits_for_int(6) + 1):
            placeholder = data_reader.read_bits_for_int(16)

            self.assertEqual(placeholder, 0)

        # amount of floors in 'test_1.ogg' = 2
        setup_header_decoder.read_floors(44)

        # amount of residues in 'test_1.ogg' = 2
        setup_header_decoder.read_residues(codebooks_configs)

        # (122632, 7)
        #
        # 95 00 00 40 | 1001_0101 0000_0000 0000_0000 0100_0000
        # 00 01 00 00 | 0000_0000 0000_0001 0000_0000 0000_0000
        # 00 00 10 40 | 0000_0000 0000_0000 0001_0000 0100_0000
        #
        # (1) [001_0101]-> previous things
        # (000) [0_0000|1]-> vorbis_mapping_count
        # (0000_0000|000)
        # (0) [1]-> flag [0]-> flag [0_0000|0000_0000||000]-> mapping type
        # [0]-> magnitude[0] [000_0000|0]-> vorbis_mapping_coupling_steps
        # (0000_000) [1]-> angle[0]
        # (0000_000) [0|0000_000]-> reserved field
        # (0000_000) [0|0000_000]-> floor number
        # (0000_000) [0|0000_000]-> residue number

        vorbis_mapping_configurations: List[SetupHeaderDecoder.MappingData] = (
            setup_header_decoder.read_mappings(2, 2, 2))

        self.assertEqual(2, len(vorbis_mapping_configurations))

        self.assertEqual(
            1, vorbis_mapping_configurations[0].vorbis_mapping_submaps)
        self.assertEqual(
            1, vorbis_mapping_configurations[0].vorbis_mapping_coupling_steps)
        self.assertEqual(
            [0], vorbis_mapping_configurations[0].vorbis_mapping_magnitude)
        self.assertEqual(
            [1], vorbis_mapping_configurations[0].vorbis_mapping_angle)
        self.assertEqual(
            [0], vorbis_mapping_configurations[0].vorbis_mapping_submap_floor)
        self.assertEqual(
            [0],
            vorbis_mapping_configurations[0].vorbis_mapping_submap_residue)

    # Optimize: NO TEST DATA
    def test_mapping_decoding_first_flag_set(self):
        pass

    def test_modes_decoding(self):
        data_reader = DataReader(PATH_TEST_1)
        setup_header_decoder: SetupHeaderDecoder = (
            SetupHeaderDecoder(data_reader))

        data_reader.read_packet()
        data_reader.read_packet()
        data_reader.read_packet()

        data_reader.byte_pointer = 8

        codebooks_configs: List[SetupHeaderDecoder.CodebookData] = []

        for i in range(44):
            codebooks_configs.append(setup_header_decoder.read_codebook())

        for i in range(data_reader.read_bits_for_int(6) + 1):
            placeholder = data_reader.read_bits_for_int(16)

            self.assertEqual(placeholder, 0)

        setup_header_decoder.read_floors(44)

        setup_header_decoder.read_residues(codebooks_configs)

        # 'test_1.ogg': amount of mappings = 2
        setup_header_decoder.read_mappings(2, 2, 2)

        # (122647, 1)
        #
        # 02          | 0000_0010                              
        # 00 00 00 00 | 0000_0000 0000_0000 0000_0000 0000_0000
        # 00 01 00 00 | 0000_0000 0000_0001 0000_0000 0000_0000
        # 00 02 02 4F | 0000_0000 0000_0010 0000_0010 0100_1111
        #
        # [0]-> blockflag [000_001]-> vorbis_mode_count [0]-> previous things
        # (0000_0000)
        # [0000_0000|0000_0000]
        # (0000_0000)
        # [0000_0000|0000_0000]
        # [0000_0000]-> vorbis_mode_mapping
        # (0000_000) [1]
        # (0000_0000|0000_000)
        # (0000_000) [0|0000_0000||0000_000]
        # (0000_0000|0000_000)
        # (0000_001) [0|0000_0000|0000_000]
        # 0000_001 [0|0000_001]-> vorbis_mode_mapping

        modes_configs: List[Tuple[bool, int]] = (
            setup_header_decoder.read_modes(2))

        self.assertEqual(
            [(False, 0), (True, 1)],
            modes_configs)


class HuffmanTests(TestCase):
    _codebook_decoder: SetupHeaderDecoder = SetupHeaderDecoder(DataReader())

    def test_1_Huffman(self):
        self._codebook_decoder._codebook_codewords_lengths = [
            None, 2, 4, 4, 4, 4, 2, 3, 3]
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


if __name__ == '__main__':
    unittest_main()
