#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def bits_to_int(bits):
    if not (isinstance(bits, basestring) and bits and all(b in ('0',
                                                                '1', )
                                                          for b in bits)):
        raise ValueError(
            "bits must be a non-empty string of 0s an 1s: '{}'".format(bits))
    return eval('0b' + bits)


def int_to_bits(value, padding=8):
    if value < 0:
        raise ValueError("Value must be positive: {}".format(value))
    res = bin(value)[2:]
    missing_padding = -len(res) % padding
    res = '0' * missing_padding + res
    return res


def bits_to_chars(bits, char_size=8):
    split_bits = (bits[s:s + char_size]
                  for s in xrange(0, len(bits), char_size))
    char_ords = (bits_to_int(bs) for bs in split_bits)
    return "".join(chr(o) for o in char_ords)


def chars_to_bits(chars, char_size=8):
    chard_ords = (ord(c) for c in chars)
    return "".join(int_to_bits(o, padding=char_size) for o in char_ords)