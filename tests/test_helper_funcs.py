from unittest import TestCase

import tests.__init__  # Without this anytask won't see tests
from vorbis.helper_funcs import *
from.test_decoders import hex_str_to_bin_str


# noinspection PyMethodMayBeStatic
class HelperFunctionsTests(TestCase):
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

    def test_bit_reverse(self):
        assert bit_reverse(1879048192) == 14
        assert bit_reverse(64424509440) == 0
        assert bit_reverse(48) == 201326592

    def test_hex_to_bin(self):
        self.assertEqual(
            hex_str_to_bin_str('00 00'),
            '0000_0000 0000_0000',
            'Zero case')
        self.assertEqual(
            hex_str_to_bin_str('23 56'),
            '0010_0011 0101_0110',
            'Ordinary case')
