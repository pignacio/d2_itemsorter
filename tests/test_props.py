#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=protected-access,invalid-name
from __future__ import absolute_import, division

import logging

from pignacio_scripts.testing import TestCase

from d2_itemsorter.props import PropertyList, PropertyDef, Property

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_TEST_PROPERTIES = {p.id: p for p in [
    PropertyDef(1, [8], 'Test prop #1: {}'),
    PropertyDef(2, [7], 'Test prop #2: {}', offsets=[32]),
    PropertyDef(3, [8, 9], 'Test prop #3: {}, {}'),
    PropertyDef(4, [9], 'Test prop #4: {}'),
]}  # yapf: disable


class PropertyListTests(TestCase):
    def setUp(self):
        super(PropertyListTests, self).setUp()
        self.prop_list = PropertyList(_TEST_PROPERTIES)

    def test_empty_from_bits(self):
        props, advanced = self.prop_list.from_bits('111111111')

        self.assertEqual(props, [])
        self.assertEqual(advanced, 9)

    def test_empty_to_bits(self):
        bits = self.prop_list.to_bits([])
        self.assertEqual(bits, '111111111')

    def test_single_field_from_bits(self):
        bits = ('100000000'  # Id = 1
                '01100001'  # Value = 134
                '111111111'  # Terminator
                )
        props, advanced = self.prop_list.from_bits(bits)

        self.assertListEqual(props,
                             [Property(definition=_TEST_PROPERTIES[1],
                                       values=[134])])
        self.assertEqual(advanced, 26)

    def test_single_field_to_bits(self):
        props = [Property(definition=_TEST_PROPERTIES[1], values=[134])]

        bits = self.prop_list.to_bits(props)

        self.assertEqual(bits,
                         ('100000000'  # Id = 1
                          '01100001'  # Value = 134
                          '111111111'  # Terminator
                          ))

    def test_offset_field_from_bits(self):
        bits = ('010000000'  # Id = 2
                '0101000'  # Value = 10 - 32 = -22
                '111111111'  # Terminator
                )
        props, advanced = self.prop_list.from_bits(bits)

        self.assertListEqual(props,
                             [Property(definition=_TEST_PROPERTIES[2],
                                       values=[-22])])
        self.assertEqual(advanced, 25)

    def test_offset_field_to_bits(self):
        props = [Property(definition=_TEST_PROPERTIES[2], values=[-22])]

        bits = self.prop_list.to_bits(props)

        self.assertEqual(bits,
                         ('010000000'  # Id = 2
                          '0101000'  # Value = 10 - 32 = -22
                          '111111111'  # Terminator
                          ))

    def test_multiple_field_from_bits(self):
        bits = ('110000000'  # Id = 3
                '11011000'  # Value = 27
                '000000001'  # Value = 256
                '111111111'  # Terminator
                )
        props, advanced = self.prop_list.from_bits(bits)

        self.assertListEqual(props,
                             [Property(definition=_TEST_PROPERTIES[3],
                                       values=[27, 256])])
        self.assertEqual(advanced, 35)

    def test_multiple_field_to_bits(self):
        props = [Property(definition=_TEST_PROPERTIES[3], values=[27, 256])]

        bits = self.prop_list.to_bits(props)

        self.assertEqual(bits,
                         ('110000000'  # Id = 3
                          '11011000'  # Value = 27
                          '000000001'  # Value = 256
                          '111111111'  # Terminator
                          ))

    def test_early_terminator_from_bits(self):
        bits = ('001000000'  # Id = 4
                '111111111'  # Value = 511
                '111111111'  # Terminator
                )
        props, advanced = self.prop_list.from_bits(bits)

        self.assertListEqual(props,
                             [Property(definition=_TEST_PROPERTIES[4],
                                       values=[511])])
        self.assertEqual(advanced, 27)

    def test_early_terminator_to_bits(self):
        props = [Property(definition=_TEST_PROPERTIES[4], values=[511])]

        bits = self.prop_list.to_bits(props)

        self.assertEqual(bits,
                         ('001000000'  # Id = 4
                          '111111111'  # Value = 511
                          '111111111'  # Terminator
                          ))
