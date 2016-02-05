#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

from pignacio_scripts.namedtuple import namedtuple_with_defaults

from .logger import Logger
from .utils import bits_to_int, int_to_bits

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Integer(object):
    def __init__(self, size):
        self._size = size

    def from_bits(self, bits):
        bits = bits[:self._size][::-1]
        return bits_to_int(bits), self._size

    def to_bits(self, val):
        if val >= 2**self._size:
            raise ValueError("Value does not fit in {} bits: {}".format(
                self._size, val))
        return int_to_bits(val, self._size)[::-1]


class Nothing(object):
    def __init__(self, size):
        self._size = size

    def from_bits(self, bits):
        return bits[:self._size], self._size

    def to_bits(self, val):
        return val[:self._size]


class Chars(object):
    def __init__(self, count, char_size=8):
        self._count = count
        self._char_size = char_size

    def from_bits(self, bits):
        values = [bits[i * self._char_size:(i + 1) * self._char_size][::-1]
                  for i in xrange(self._count)]
        chars = [chr(bits_to_int(v)) for v in values if v]
        return "".join(chars), self._count * self._char_size

    def to_bits(self, chars):
        values = [int_to_bits(
            ord(c),
            padding=self._char_size)[::-1] for c in chars]
        return "".join(values)


class Until(object):
    def __init__(self, patterns):
        self._patterns = patterns

    def from_bits(self, bits):
        def get_index(pattern, bits):
            try:
                return bits.index(pattern)
            except ValueError:
                return len(bits)

        min_index = min(get_index(p, bits) for p in self._patterns)

        return bits[:min_index], min_index

    def to_bits(self, val):  # pylint: disable=no-self-use
        return val


SchemaPiece = namedtuple_with_defaults(
    'SchemaPiece',
    ['field', 'type', 'condition', 'multiple'],
    defaults={'condition': None,
              'multiple': None})


class ParseError(Exception):
    pass


class BinarySchema(object):
    UNPARSED_FIELD = '__unparsed'

    def __init__(self, schema):
        self._schema = schema

    def from_bits(self, binary_str):
        position = 0
        res = collections.OrderedDict()
        for piece in self._schema:
            type_ = (Nothing(piece.type) if isinstance(piece.type, (int, long))
                     else piece.type)
            if self._should_parse(piece, res):
                logger.debug("Parsing %s from position %s/%s", piece.field,
                             position, len(binary_str))
                logger.debug("Str: %s%s", binary_str[position:position + 50],
                             '[...]'
                             if len(binary_str) > position + 50 else '')
                if piece.multiple:
                    if isinstance(piece.multiple, (int, long)):
                        count = piece.multiple
                    else:
                        count = piece.multiple(res)
                    values = []
                    for _ in xrange(count):
                        if position >= len(binary_str):
                            raise ParseError("EOD!")
                        bits = binary_str[position:]
                        value, advance = type_.from_bits(bits)
                        position += advance
                        values.append(value)
                    res[piece.field] = values
                else:
                    if position >= len(binary_str):
                        raise ParseError("EOD!")
                    bits = binary_str[position:]
                    res[piece.field], advance = type_.from_bits(bits)
                    position += advance

        return res, position

    def to_bits(self, values):
        res = ''
        for piece in self._schema:
            type_ = (Nothing(piece.type) if isinstance(piece.type, (int, long))
                     else piece.type)
            if self._should_parse(piece, values):
                if piece.multiple:
                    if isinstance(piece.multiple, (int, long)):
                        count = piece.multiple
                    else:
                        count = piece.multiple(values)
                    if len(values[piece.field]) != count:
                        Logger.warn(
                            "Unexpected size for a multiple: {} (Expected {})",
                            len(values[piece.field]), count)
                    for value in values[piece.field]:
                        res += type_.to_bits(value)
                else:
                    res += type_.to_bits(values[piece.field])
        return res

    def decode(self, binary_str):
        res, position = self.from_bits(binary_str)
        unparsed = binary_str[position:]
        if unparsed:
            res[self.UNPARSED_FIELD] = unparsed
        return res

    def encode(self, values):
        res = self.to_bits(values)
        return res + values.get(self.UNPARSED_FIELD, '')

    @staticmethod
    def _should_parse(piece, values):
        if piece.condition is None:
            return True
        elif isinstance(piece.condition, basestring):
            return values.get(piece.condition)
        else:
            return piece.condition(values)
