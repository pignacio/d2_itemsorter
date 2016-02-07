#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections

from pignacio_scripts.namedtuple import namedtuple_with_defaults

from .logger import Logger
from .schema import Integer, BinarySchema, SchemaPiece

PropertyDef = namedtuple_with_defaults('PropertyDef',
                                       ['id', 'field_sizes', 'fmt_string',
                                        'offsets'],
                                       defaults={'offsets': None})
_Property = collections.namedtuple('Property', ['definition', 'values'])


class Property(_Property):
    __slots__ = ()

    def as_game_str(self):
        return self.definition.fmt_string.format(*self.values)

_PROPERTIES = {p.id: p for p in [
    PropertyDef(0, [10], '{:+d} to Strength', offsets=[32]),
    PropertyDef(1, [10], '{:+d} to Energy', offsets=[32]),
    PropertyDef(2, [10], '{:+d} to Dexterity', offsets=[32]),
    PropertyDef(3, [10], '{:+d} to Vitality', offsets=[32]),
    PropertyDef(7, [10], '{:+d} to Life', offsets=[32]),
    PropertyDef(9, [10], '{:+d} to Mana', offsets=[32]),
    PropertyDef(11, [10], '{:+d} Maximum Stamina', offsets=[32]),
    PropertyDef(19, [10], '{:+d} to Attack Rating'),
    PropertyDef(22, [9], '{:+d} to Maximum Damage'),
    PropertyDef(24, [9], '{:+d} to Maximum Damage'),
    PropertyDef(31, [11], '{:+d} Defense', offsets=[10]),
    PropertyDef(34, [16], 'Damage Reduced by {:d}'),
    PropertyDef(35, [16], 'Magic Damage Reduced by {:d}'),
    PropertyDef(37, [8], 'Magic Resist {:+d}%', offsets=[50]),
    PropertyDef(39, [8], 'Fire Resist {:+d}%', offsets=[50]),
    PropertyDef(41, [8], 'Lightning Resist {:+d}%', offsets=[50]),
    PropertyDef(43, [8], 'Cold Resist {:+d}%', offsets=[50]),
    PropertyDef(45, [8], 'Poison Resist {:+d}%', offsets=[50]),
    PropertyDef(60, [8], '{:d}% Life Stolen per Hit', offsets=[50]),
    PropertyDef(74, [16], '+{:d} Replenish Life', offsets=[3000]),
    PropertyDef(79, [13], '{:d}% Extra Gold from Monsters'),
    PropertyDef(80, [13], '{:d}% Better Chance of Getting Magic Items'),
    PropertyDef(85, [12], '{:d}% to Experience Gained', offsets=[50]),
    PropertyDef(89, [5], '{:+d} to Light Radius', offsets=[12]),
    PropertyDef(96, [9], '{:+d}% Faster Run/Walk', offsets=[100]),
    PropertyDef(105, [9], '{:+d}% Faster Cast Rate', offsets=[50]),
    PropertyDef(109, [9], 'Shorter Curse Duration {:+d}%', offsets=[100]),
    PropertyDef(110, [8], 'Poison Length Reduced by {:+d}%', offsets=[20]),
    PropertyDef(118, [1], 'Half Freeze Duration'),
    PropertyDef(138, [7], '{:+d} to Mana after each Kill'),
    PropertyDef(141, [8], '{:d}% Deadly Strike'),
    PropertyDef(160, [10], '{:+d} to Maximum Damage'),
    PropertyDef(357, [12], '{:+d}% to Magic Skill Damage', offsets=[50]),
    PropertyDef(367, [8], 'Dexterity bonus {:d}%', offsets=[10]),
]}  # yapf: disable

_LIST_TERMINATOR = 0x1ff

MISSING_PROPERTY_IDS = set()


class PropertyList(object):
    def __init__(self, properties=None, terminator=None):
        self._properties = _PROPERTIES if properties is None else properties
        self._terminator = _LIST_TERMINATOR if terminator is None else terminator

    def from_bits(self, bits, **kwargs):
        position = 0
        properties = []
        while True:
            prop_id, advanced = Integer(9).from_bits(bits[position:])
            position += advanced
            if prop_id == self._terminator:
                break
            try:
                prop_def = self._properties[prop_id]
            except KeyError:
                MISSING_PROPERTY_IDS.add(prop_id)
                Logger.warn('Unknown property ID: "{}"', prop_id)
                position -= advanced
                break
            else:
                values, advanced = self._get_fields_schema(prop_def).from_bits(
                    bits[position:])
                position += advanced
                values = [values[i] for i in xrange(len(values))]
                if prop_def.offsets is not None:
                    values = [v - prop_def.offsets[i]
                              for i, v in enumerate(values)]
                properties.append(Property(prop_def, values))

        return properties, position

    def to_bits(self, properties, **kwargs):
        res = ''
        for prop in properties:
            res += Integer(9).to_bits(prop.definition.id)
            values = prop.values
            if prop.definition.offsets:
                values = [v + prop.definition.offsets[i]
                          for i, v in enumerate(values)]
            res += self._get_fields_schema(prop.definition).to_bits(
                {i: v
                 for i, v in enumerate(values)})
        res += Integer(9).to_bits(self._terminator)
        return res

    @staticmethod
    def _get_fields_schema(prop_def):
        return BinarySchema((SchemaPiece(i, Integer(s))
                             for i, s in enumerate(prop_def.field_sizes)))
