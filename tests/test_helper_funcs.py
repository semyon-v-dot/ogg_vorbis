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

from vorbis.helper_funcs import (
    ilog, float32_unpack, lookup1_values, bit_reverse)
from .test_decoders import hex_str_to_bin_str


# noinspection PyMethodMayBeStatic
class HelperFunctionsTests(TestCase):
    def test_ilog_zero(self):
        self.assertEqual(ilog(0), 0)

    def test_ilog_positive_number(self):
        self.assertEqual(ilog(1), 1)
        self.assertEqual(ilog(7), 3)

    def test_ilog_negative_number(self):
        self.assertEqual(ilog(-1111), 0)
        self.assertEqual(ilog(-112312), 0)

    def test_lookup1_values(self):
        self.assertEqual(lookup1_values(50, 3), 3)
        self.assertEqual(lookup1_values(1, 3), 1)

    def test_float32_unpack_positive_number(self):
        self.assertEqual(float32_unpack(0x60A03250), 12880 * pow(2, -15))

    def test_float32_unpack_negative_number(self):
        self.assertEqual(float32_unpack(0xE0A03250), -12880 * pow(2, -15))
        self.assertEqual(
            float32_unpack(0b11100000000100000000000000000000), -1.0)

    def test_bit_reverse(self):
        self.assertEqual(
            bit_reverse(0b1110000000000000000000000000000), 14)
        self.assertEqual(
            bit_reverse(0b110000), 0b00001100000000000000000000000000)

    def test_bit_reverse_greater_than_2_exponent_32(self):
        self.assertEqual(
            bit_reverse(0b111100000000000000000000000000000000), 0)

    def test_hex_to_bin(self):
        self.assertEqual(
            hex_str_to_bin_str('00 00'),
            '0000_0000 0000_0000',
            'Zero case')
        self.assertEqual(
            hex_str_to_bin_str('23 56'),
            '0010_0011 0101_0110',
            'Ordinary case')


if __name__ == '__main__':
    unittest_main()
