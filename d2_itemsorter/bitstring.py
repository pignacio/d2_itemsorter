#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class BitString(object):

    """Docstring for BitString. """

    def __init__(self, bits, start=None, end=None, reverse_bits=None):
        self._bits = bits
        self._bits_size = len(self._bits)
        self._reverse_bits = reverse_bits if reverse_bits is not None else bits[::-1]
        self._start = self._bits_index(start) if start is not None else 0
        self._end = self._bits_index(end) if end is not None else len(bits)
        assert self._start <= self._end, "start should be before end"
        self._size = self._end - self._start

    def index(self, pattern):
        value = self._bits.index(pattern, self._start)
        if value + len(pattern) > self._end:
            raise ValueError("substring not found")
        return value - self._start

    def as_string(self):
        return self._bits[self._start:self._end]

    def __getitem__(self, index):
        if isinstance(index, slice):
            if index.step:
                if index.step != -1 or index.start is not None or index.stop is not None:
                    raise ValueError("Cannot handle steps different than [::-1].")
                return BitString(self._reverse_bits,
                                 start=self._bits_size - self._end,
                                 end=self._bits_size - self._start,
                                 reverse_bits=self._bits)
            start = self.__hoist(index.start) if index.start is not None else self._start
            stop = self.__hoist(index.stop) if index.stop is not None else self._end
            return BitString(self._bits, start, stop, reverse_bits=self._reverse_bits)

        self.__assert_index(index)
        return self._bits[self.__index(index)]

    def __len__(self):
        return self._end - self._start

    def __index(self, index):
        return self._start + index if index >= 0 else self._end + index

    def __hoist(self, index):
        return self.__index(max(-self._size, min(self._size, index)))

    def _bits_index(self, index):
        if not -self._bits_size <= index <= self._bits_size:
            raise ValueError("Invalid index: {}".format(index))
        return index if index >= 0 else self._bits_size + index

    def __str__(self):
        return "BitString({!r})".format(self._bits[self._start:self._end])

    def __assert_index(self, index):
        if not -self._size <= index < self._size:
            raise IndexError("Index out of range: {}".format(index))
