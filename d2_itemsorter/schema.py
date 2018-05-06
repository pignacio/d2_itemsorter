#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

from pignacio_scripts.namedtuple import namedtuple_with_defaults

from .bitstring import BitString
from .logger import Logger
from .utils import bits_to_int, int_to_bits

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def as_string(thing):
    if isinstance(thing, BitString):
        return thing.as_string()
    return thing


class Integer(object):
    def __init__(self, size):
        self._size = size

    def from_bits(self, bits, **kwargs):
        bits = bits[:self._size][::-1]
        return bits_to_int(bits), self._size

    def to_bits(self, val, **kwargs):
        if val >= 2**self._size:
            raise ValueError("Value does not fit in {} bits: {}".format(
                self._size, val))
        return int_to_bits(val, self._size)[::-1]


class Nothing(object):
    def __init__(self, size):
        self._size = size

    def from_bits(self, bits, **kwargs):
        return bits[:self._size], self._size

    def to_bits(self, val, **kwargs):
        return val[:self._size]


class Chars(object):
    def __init__(self, count, char_size=8):
        self._count = count
        self._char_size = char_size

    def from_bits(self, bits, **kwargs):
        values = [bits[i * self._char_size:(i + 1) * self._char_size][::-1]
                  for i in xrange(self._count)]
        chars = [chr(bits_to_int(v)) for v in values if v]
        return "".join(chars), self._count * self._char_size

    def to_bits(self, chars, **kwargs):
        values = [int_to_bits(
            ord(c),
            padding=self._char_size)[::-1] for c in chars]
        return "".join(values)


class NullTerminatedChars(object):
    def __init__(self, char_size=8):
        self._char_size = char_size

    def from_bits(self, bits, **kwargs):
        count = 0
        null = "0" * self._char_size

        def _next():
            return bits[self._char_size * count:self._char_size * (count + 1)]

        while _next() not in ('', null):
            count += 1

        values = [bits[i * self._char_size:(i + 1) * self._char_size][::-1]
                  for i in xrange(count)]
        chars = [chr(bits_to_int(v)) for v in values if v]
        return "".join(chars), (count + 1) * self._char_size

    def to_bits(self, chars, **kwargs):
        values = [int_to_bits(
            ord(c),
            padding=self._char_size)[::-1] for c in chars]
        return "".join(values) + "0" * self._char_size


class Until(object):
    def __init__(self, patterns):
        self._patterns = patterns

    def from_bits(self, bits, **kwargs):
        def get_index(pattern, bits):
            try:
                return bits.index(pattern)
            except ValueError:
                return len(bits)

        min_index = min(get_index(p, bits) for p in self._patterns)

        return bits[:min_index], min_index

    def to_bits(self, val, **kwargs):  # pylint: disable=no-self-use
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
    PARENT_FIELD = '__parent'

    def __init__(self, schema):
        self._schema = schema

    def from_bits(self, binary_str, parent=None, **kwargs):
        position = 0
        res = collections.OrderedDict()
        res[self.PARENT_FIELD] = parent
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
                        value, advance = type_.from_bits(bits, parent=res)
                        position += advance
                        values.append(value)
                    res[piece.field] = values
                else:
                    if position > len(binary_str):
                        raise ParseError("EOD!")
                    bits = binary_str[position:]
                    res[piece.field], advance = type_.from_bits(bits, parent=res)
                    position += advance

        res['__origin'] = binary_str[:position]
        del res[self.PARENT_FIELD]
        return res, position

    def to_bits(self, values, parent=None, **kwargs):
        res = ''
        values = collections.OrderedDict(values)
        values[self.PARENT_FIELD] = parent
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
                        res += as_string(type_.to_bits(value, parent=values))
                else:
                    res += as_string(type_.to_bits(values[piece.field], parent=values))
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

    @classmethod
    def _should_parse(cls, piece, values):
        if piece.condition is None:
            return True
        elif isinstance(piece.condition, basestring):
            if piece.condition.startswith('..'):
                return values[cls.PARENT_FIELD].get(piece.condition[2:])
            return values.get(piece.condition)
        else:
            return piece.condition(values)
