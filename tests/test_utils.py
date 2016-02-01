#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=protected-access,invalid-name
from __future__ import absolute_import, division

import logging

from pignacio_scripts.testing.testcase import TestCase

from d2_itemsorter.utils import (bits_to_int, int_to_bits, bytes_to_bits,
                                 bits_to_bytes, bits_to_chars, chars_to_bits)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitsToIntTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.bits_to_int`.'''

    def test_zero(self):
        self.assertEqual(bits_to_int('0'), 0)

    def test_one(self):
        self.assertEqual(bits_to_int('1'), 1)

    def test_full_byte(self):
        self.assertEqual(bits_to_int('11111111'), 255)

    def test_two_bytes(self):
        self.assertEqual(bits_to_int('100000000'), 256)
        self.assertEqual(bits_to_int('111111111'), 511)

    def test_padding(self):
        self.assertEqual(bits_to_int('110'), 6)
        self.assertEqual(bits_to_int('0110'), 6)
        self.assertEqual(bits_to_int('00110'), 6)
        self.assertEqual(bits_to_int('00000110'), 6)
        self.assertEqual(bits_to_int('000000110'), 6)

    def test_raises_if_not_binary(self):
        self.assertRaises(ValueError, bits_to_int, 'x')
        self.assertRaises(ValueError, bits_to_int, '0b0')
        self.assertRaises(ValueError, bits_to_int, 'abc')
        self.assertRaises(ValueError, bits_to_int, '102010')


class IntToBitsTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.int_to_bits`.'''

    def test_zero(self):
        self.assertEqual(int_to_bits(0), '00000000')

    def test_one(self):
        self.assertEqual(int_to_bits(1), '00000001')

    def test_full_byte(self):
        self.assertEqual(int_to_bits(255), '11111111')

    def test_two_bytes(self):
        self.assertEqual(int_to_bits(256), '0000000100000000')
        self.assertEqual(int_to_bits(511), '0000000111111111')

    def test_padding(self):
        self.assertEqual(int_to_bits(127), '01111111')
        self.assertEqual(int_to_bits(127, padding=2), '01111111')
        self.assertEqual(int_to_bits(127, padding=3), '001111111')
        self.assertEqual(int_to_bits(127, padding=5), '0001111111')
        self.assertEqual(int_to_bits(127, padding=6), '000001111111')
        self.assertEqual(int_to_bits(127, padding=7), '1111111')

    def test_negative(self):
        self.assertRaises(ValueError, int_to_bits, -1)


class BitsToBytesTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.bits_to_bytes`.'''

    def test_one_byte(self):
        self.assertEqual(bits_to_bytes('01010000'), [10])

    def test_multiple_bytes(self):
        self.assertEqual(bits_to_bytes('100000000100000000100000'), [1, 2, 4])


class BytesToBitsTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.bytes_to_bits`.'''

    def test_one_byte(self):
        self.assertEqual(bytes_to_bits([19]), '11001000')

    def test_multiple_bytes(self):
        self.assertEqual(
            bytes_to_bits([255, 128, 16]), '111111110000000100001000')

    def test_negative(self):
        self.assertRaises(ValueError, bytes_to_bits, [-1])


class BitsToCharsTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.bits_to_chars`.'''

    def test_bit_order(self):
        self.assertEqual(bits_to_chars("0100000011111101"), '\x02\xbf')

    def test_ascii(self):
        self.assertEqual(
            bits_to_chars("100001100101111010000010010110100000110010011100"),
            'azAZ09')

    def test_char_size(self):
        self.assertEqual(
            bits_to_chars("000100100001011",
                          char_size=5),
            '\x08\x02\x1a')


class CharsToBitsTests(TestCase):
    ''' Tests for `d2_itemsorter.utils.chars_to_bits`.'''

    def test_bit_order(self):
        self.assertEqual(chars_to_bits("\x02\xbf"), '0100000011111101')

    def test_ascii(self):
        self.assertEqual(
            chars_to_bits("azAZ09"),
            '100001100101111010000010010110100000110010011100')

    def test_char_size(self):
        self.assertEqual(
            chars_to_bits('\x08\x02\x1a',
                          char_size=5),
            '000100100001011')
