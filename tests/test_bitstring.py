#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=protected-access,invalid-name
from __future__ import absolute_import, division

import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

from pignacio_scripts.testing import TestCase

from d2_itemsorter.bitstring import BitString

_TRUE = "1"
_FALSE = "0"

class BitStringTest():
    def _assert_matches_string(self, bitstring, expected):
        print bitstring, expected
        assert all(b in "01" for b in expected)
        self.assertEquals(expected, bitstring.as_string())
        for index, bit in enumerate(expected):
            expected_bit = _TRUE if bit == "1" else _FALSE
            self.assertEquals(expected_bit, bitstring[index], "index {}".format(index))
            negative_index = index - len(expected)
            self.assertEquals(expected_bit, bitstring[negative_index], "index {}".format(negative_index))

    def test_len(self):
        self.assertEquals(len(self.bitstring), 6)

    def test_get_by_valid_positive_index(self):
        self.assertEquals(_FALSE, self.bitstring[0], "index 0")
        self.assertEquals(_TRUE, self.bitstring[1], "index 1")
        self.assertEquals(_FALSE, self.bitstring[2], "index 2")
        self.assertEquals(_FALSE, self.bitstring[3], "index 3")
        self.assertEquals(_TRUE, self.bitstring[4], "index 4")
        self.assertEquals(_TRUE, self.bitstring[5], "index 5")

    def test_get_by_valid_negative_index(self):
        self.assertEquals(_TRUE, self.bitstring[-1], "index -1")
        self.assertEquals(_TRUE, self.bitstring[-2], "index -2")
        self.assertEquals(_FALSE, self.bitstring[-3], "index -3")
        self.assertEquals(_FALSE, self.bitstring[-4], "index -4")
        self.assertEquals(_TRUE, self.bitstring[-5], "index -5")
        self.assertEquals(_FALSE, self.bitstring[-6], "index -6")

    def test_get_by_invalid_indexes(self):
        self.assertRaises(IndexError, lambda: self.bitstring[6])
        self.assertRaises(IndexError, lambda: self.bitstring[-7])
        self.assertRaises(IndexError, lambda: self.bitstring[12])
        self.assertRaises(IndexError, lambda: self.bitstring[-24])

    def test_positive_splicing(self):
        self._assert_matches_string(self.bitstring[2:], "0011")
        self._assert_matches_string(self.bitstring[1:4], "100")
        self._assert_matches_string(self.bitstring[:5], "01001")
        self._assert_matches_string(self.bitstring[2:8], "0011")
        self._assert_matches_string(self.bitstring[9:], "")
        self._assert_matches_string(self.bitstring[10:11], "")

    def test_negative_splicing(self):
        self._assert_matches_string(self.bitstring[-2:], "11")
        self._assert_matches_string(self.bitstring[-4:-1], "001")
        self._assert_matches_string(self.bitstring[:-5], "0")
        self._assert_matches_string(self.bitstring[-8:-3], "010")
        self._assert_matches_string(self.bitstring[:-9], "")
        self._assert_matches_string(self.bitstring[-11:-10], "")

    def test_reverse_splicing(self):
        self._assert_matches_string(self.bitstring[::-1], "110010")
        self._assert_matches_string(self.bitstring[::-1][::-1], "010011")


class UnboundedBitStringTest(BitStringTest, TestCase):
    def setUp(self):
        super(UnboundedBitStringTest, self).setUp()
        self.bitstring = BitString("010011")


class BoundedBitStringTest(BitStringTest, TestCase):
    def setUp(self):
        super(BoundedBitStringTest, self).setUp()
        self.bitstring = BitString("111010011000", 3, -3)
