#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def bits_to_int(bits):
    value = 0
    for index in xrange(len(bits)):
        value *= 2
        bit = bits[index]
        if bit == '1':
            value += 1
        elif bit != '0':
            raise ValueError(
                "Invalid bit at index {}: {} (Must be 0/1)".format(index, bit))
    return value


def int_to_bits(value, padding=8):
    if not isinstance(value, (int, long)):
        raise ValueError("Value must be an integer: {!r}".format(value))
    if value < 0:
        raise ValueError("Value must be positive: {}".format(value))
    res = bin(value)[2:]
    missing_padding = -len(res) % padding
    res = '0' * missing_padding + res
    return res


def bytes_to_bits(bytes_):
    for index, byte in enumerate(bytes_):
        if not 0 <= byte < 256:
            raise ValueError("Invalid byte value at index {}: {}".format(index,
                                                                         byte))
    return "".join(int_to_bits(b)[::-1] for b in bytes_)


def bits_to_bytes(bits):
    return [bits_to_int(bits[s:s + 8][::-1]) for s in xrange(0, len(bits), 8)]


def bits_to_str(bits, char_size=8):
    split_bits = (bits[s:s + char_size]
                  for s in xrange(0, len(bits), char_size))
    char_ords = (bits_to_int(bs[::-1]) for bs in split_bits)
    return "".join(chr(o) for o in char_ords)


def str_to_bits(chars, char_size=8):
    char_ords = (ord(c) for c in chars)
    return "".join(int_to_bits(o, padding=char_size)[::-1] for o in char_ords)
