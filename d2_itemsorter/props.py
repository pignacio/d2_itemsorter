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
PropList = collections.namedtuple('PropList', ['properties', 'terminated'])


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
    PropertyDef(16, [9], '{:+d}% Enhanced Defense'),
    PropertyDef(17, [9, 9], '{:+d}% Enhanced Damage'),
    PropertyDef(19, [10], '{:+d} to Attack Rating'),
    PropertyDef(20, [6], '{:+d}% Increased Chance of Blocking'),
    PropertyDef(21, [8], '{:+d} to Minimum Damage'),
    PropertyDef(22, [9], '{:+d} to Maximum Damage'),
    PropertyDef(23, [8], '{:+d} to Minimum Damage'),
    PropertyDef(24, [9], '{:+d} to Maximum Damage'),
    PropertyDef(27, [8], 'Regenerate Mana {:d}%'),
    PropertyDef(28, [8], 'Heal Stamina Plus {:d}%'),
    PropertyDef(31, [11], '{:+d} Defense', offsets=[10]),
    PropertyDef(32, [10], '{:+d} Defense vs. Missile'),
    PropertyDef(33, [10], '{:+d} Defense vs. Melee'),
    PropertyDef(34, [16], 'Damage Reduced by {:d}'),
    PropertyDef(35, [16], 'Magic Damage Reduced by {:d}'),
    PropertyDef(36, [8], 'Damage Reduced by {:+d}%'),
    PropertyDef(37, [8], 'Magic Resist {:+d}%', offsets=[50]),
    PropertyDef(38, [5], '+{:d}% to Maximum Magic Resist'),
    PropertyDef(39, [8], 'Fire Resist {:+d}%', offsets=[50]),
    PropertyDef(40, [5], '+{:d}% to max fire resist'),
    PropertyDef(41, [8], 'Lightning Resist {:+d}%', offsets=[50]),
    PropertyDef(42, [5], '+{:d}% to max lightning resist'),
    PropertyDef(43, [8], 'Cold Resist {:+d}%', offsets=[50]),
    PropertyDef(44, [5], '+{:d}% to max cold resist'),
    PropertyDef(45, [8], 'Poison Resist {:+d}%', offsets=[50]),
    PropertyDef(46, [5], '{:+d} to max Poison Resist'),
    PropertyDef(48, [10, 11], 'Adds {:d}-{:d} fire damage'),
    PropertyDef(50, [10, 11], 'Adds {:d}-{:d} lightning damage'),
    PropertyDef(52, [10, 11], 'Adds {:d}-{:d} magic damage'),
    PropertyDef(54, [10, 11, 10], 'Adds {:d}-{:d} cold damage'),
    PropertyDef(57, [13, 13, 16], '+({:d}-{:d})/256 poison damage over {:d}/25 s'),
    PropertyDef(60, [8], '{:d}% Life Stolen per Hit', offsets=[50]),
    PropertyDef(62, [8], '{:d}% Mana Stolen per Hit', offsets=[50]),
    PropertyDef(66, [12], 'Hit Stuns Enemies <{:d}>'),
    PropertyDef(73, [9], '[?][73] <{:d}>'),
    PropertyDef(74, [16], '+{:d} Replenish Life', offsets=[3000]),
    PropertyDef(75, [7], 'Increased Maximum Durability {:d}%', offsets=[20]),
    PropertyDef(76, [8], 'Increase Maximum Life {:d}%', offsets=[10]),
    PropertyDef(77, [8], 'Increase Maximum Mana {:d}%', offsets=[10]),
    PropertyDef(78, [16], 'Attacker takes damage of {:d}'),
    PropertyDef(79, [13], '{:d}% Extra Gold from Monsters'),
    PropertyDef(80, [13], '{:d}% Better Chance of Getting Magic Items'),
    PropertyDef(81, [7], 'Knockback'),
    PropertyDef(83, [3, 5], '+{1:d} to Class<{0:d}> Skill Levels'),
    PropertyDef(85, [12], '{:d}% to Experience Gained', offsets=[50]),
    PropertyDef(86, [7], '{:+d} Life after each Kill'),
    PropertyDef(87, [7], 'Reduces all Vendor Prices {:d}%'),
    PropertyDef(89, [5], '{:+d} to Light Radius', offsets=[12]),
    PropertyDef(91, [12], 'Requirements {:+d}%', offsets=[100]),
    PropertyDef(92, [12], 'Unknown<92>: {:+d}'),
    PropertyDef(93, [9], '{:+d}% Increased Attack Speed', offsets=[20]),
    PropertyDef(96, [9], '{:+d}% Faster Run/Walk', offsets=[100]),
    PropertyDef(97, [10, 7], '+{1:d} to Skill<{0:d}> (All) [97]'),
    PropertyDef(98, [10], 'ConvertTo[?]<98>: {:d}'),
    PropertyDef(99, [8], '{:+d}% Faster Hit Recovery', offsets=[20]),
    PropertyDef(102, [8], '{:+d}% Faster Block Rate', offsets=[20]),
    PropertyDef(105, [9], '{:+d}% Faster Cast Rate', offsets=[50]),
    PropertyDef(107, [10, 7], '+{1:d} to Skill<{0:d}> (Class Only) [107]'),
    PropertyDef(108, [3], 'Slain Monster Rest in Peace <{:+d}>%'),
    PropertyDef(109, [9], 'Shorter Curse Duration {:+d}%', offsets=[100]),
    PropertyDef(110, [8], 'Poison Length Reduced by {:d}%', offsets=[20]),
    PropertyDef(112, [7], 'Hit Causes Monster to Flee {:d}%', offsets=[10]),
    PropertyDef(113, [7], 'Hit Blinds Target ({:d})'),
    PropertyDef(114, [7], '{:d}% Damage Taken Goes To Mana'),
    PropertyDef(115, [1], 'Ignore Target\'s Defense'),
    PropertyDef(116, [7], '-{:d}% Target Defense'),
    PropertyDef(117, [7], 'Prevent Monster Heal'),
    PropertyDef(118, [1], 'Half Freeze Duration'),
    PropertyDef(119, [12], '{:+d}% Bonus to Attack Rating', offsets=[20]),
    PropertyDef(120, [7], '{:+d} to Monster Defense Per Hit', offsets=[128]),
    PropertyDef(121, [12], '{:+d}% Damage to Demons', offsets=[20]),
    PropertyDef(122, [12], '{:+d}% Damage to Undead', offsets=[20]),
    PropertyDef(123, [13], '{:+d} to Attack Rating against Demons', offsets=[128]),
    PropertyDef(124, [13], '{:+d} to Attack Rating against Undead', offsets=[128]),
    PropertyDef(127, [5], '+{:d} to All Skills'),
    PropertyDef(128, [16], 'Attacker Takes Lightning Damage of {:+d}'),
    PropertyDef(134, [5], 'Freezes Target <{:d}>'),
    PropertyDef(135, [9], '{:d}% Chance of Open Wounds'),
    PropertyDef(136, [9], '{:d}% Chance of Crushing Blow'),
    PropertyDef(138, [7], '{:+d} to Mana after each Kill'),
    PropertyDef(139, [7], '{:+d} to Life after each Kill'),
    PropertyDef(140, [7], 'Unknown<140>: {:d}'),
    PropertyDef(141, [8], '{:d}% Deadly Strke'),
    PropertyDef(142, [8], 'Fire Absorb {:d}%'),
    PropertyDef(143, [16], '{:d} Fire Absorb'),
    PropertyDef(144, [8], 'Lightning Absorb {:d}%'),
    PropertyDef(145, [16], '{:d} Lightning Absorb'),
    PropertyDef(146, [8], 'Magic Absorb {:d}%'),
    PropertyDef(147, [16], '{:d} Magic Absorb'),
    PropertyDef(148, [8], 'Cold Absorb {:d}%'),
    PropertyDef(149, [16], '{:d} Cold Absorb'),
    PropertyDef(150, [7], 'Slows Target by {:d}%'),
    PropertyDef(151, [10, 8], 'Level {1:d} Skill<{0:d}> When Equipped'),
    PropertyDef(152, [1], 'Indestructible'),
    PropertyDef(153, [1], 'Cannot Be Frozen'),
    PropertyDef(154, [8], '{:+d}% Slower Stamina Drain', offsets=[90]),
    PropertyDef(155, [10, 7], '{1:d}% reanimate as: Mob<{0:d}>'),
    PropertyDef(156, [7], 'Piercing Attack <{:d}>'),
    PropertyDef(157, [7], 'Fires Magic Arrows <{:d}>'),
    PropertyDef(158, [7], 'Fires Explosive Arrows or Bolds <{:d}>'),
    PropertyDef(159, [9], '{:+d} to Minimum Damage'),
    PropertyDef(160, [10], '{:+d} to Maximum Damage'),
    PropertyDef(181, [9], '[?][181] ??? <{:d}>'),
    PropertyDef(188, [16, 3], '+{1:d} to Skill<{0:d}> [188][?]'),  # TODO: unconfirmed, looks weird
    PropertyDef(195, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> on attack'),
    PropertyDef(196, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> when you Kill an Enemy'),
    PropertyDef(197, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> when you Die'),
    PropertyDef(198, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> on striking'),
    PropertyDef(201, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> when struck'),
    PropertyDef(204, [6, 10, 8, 8], 'Level {:d} Skill<{:d}> ({:d}/{:d} charges)'),
    PropertyDef(214, [6], '{:+d}/8 to Defense (Based on Character Level)'),
    PropertyDef(215, [6], '{:+d}/16% Enhanced Defense (Based on Character Level)'),
    PropertyDef(217, [6], '{:+d}/16 to Mana (Based on Character Level)'),
    PropertyDef(218, [6], '{:+d}/16 to Maximum Damage (Based on Character Level)'),
    PropertyDef(220, [6], '{:+d}/16 to Strength (Based on Character Level)'),
    PropertyDef(221, [6], '{:+d}/16 to Dexterity (Based on Character Level)'),
    PropertyDef(222, [6], '{:+d}/16 to Energy (Based on Character Level)'),
    PropertyDef(224, [6], '{:+d}/2 to Attack Rating (Based on Character Level)'),
    PropertyDef(225, [6], '{:+d}/8% Bonus to Attack Rating (Based on Character Level)'),
    PropertyDef(228, [6], 'Indestructible [?]'),
    PropertyDef(230, [6], 'Cold Resist {:d}/16 (Based on Character Level)'),
    PropertyDef(231, [6], 'Fire Resist {:d}/16 (Based on Character Level)'),
    PropertyDef(232, [6], '{:+d}/16 to Lightning Resist (Based on Character Level)'),
    PropertyDef(233, [6], '{:+d}/16 to Poison Resist (Based on Character Level)'),
    PropertyDef(239, [6], '{:+d}/16 Extra Gold form Monsters (Based on Character Level)'),
    PropertyDef(240, [6], '{:+d}/16 Better Chance of Getting Magic Items (Based on Character Level)'),
    PropertyDef(252, [6], 'Repairs 1 durability in 100/{:d} seconds'),
    PropertyDef(253, [8], 'Replenishes Quantity ({:+d}/??)[?]'),
    PropertyDef(254, [8], 'Increaed Stack Size ({:+d})'),
    PropertyDef(329, [12], '{:+d}% to Fire Skill Damage', offsets=[50]),
    PropertyDef(330, [12], '{:+d}% to Lightning Skill Damage', offsets=[50]),
    PropertyDef(331, [12], '{:+d}% to Cold Skill Damage', offsets=[50]),
    PropertyDef(332, [12], '{:+d}% to Poison Skill Damage', offsets=[50]),
    PropertyDef(333, [9], '-{:d}% to Enemy Lightning Resistance'),
    PropertyDef(334, [9], '-{:d}% to Enemy Lightning Resistance'),
    PropertyDef(335, [9], '-{:d}% to Enemy Cold Resistance'),
    PropertyDef(336, [9], '-{:d}% to Enemy Poison Resistance'),
    PropertyDef(338, [7], 'Chance to dodge melee attack when still +{:d}%'),
    PropertyDef(339, [7], 'Chance to dodge missile attack when still +{:d}%'),
    PropertyDef(340, [7], 'Chance to dodge attacks when moving +{:d}%'),
    PropertyDef(349, [8], 'Elemental resistance of summons {:+d}%'),
    PropertyDef(357, [12], '{:+d}% to Magic Skill Damage', offsets=[50]),
    PropertyDef(359, [12], 'Magic Affinity Bonus {:+d}%', offsets=[100]),
    PropertyDef(362, [12], 'Extra Throwing Potion Damage +{:d}%'),
    PropertyDef(365, [8], 'Strength bonus {:d}%', offsets=[10]),
    PropertyDef(366, [8], 'Energy bonus {:d}%', offsets=[10]),
    PropertyDef(367, [8], 'Dexterity bonus {:d}%', offsets=[10]),
    PropertyDef(372, [8], '[?][372] <{:d}>'),
    PropertyDef(388, [9], '{:d}% Extra Base Life to Summons', offsets=[50]),
    PropertyDef(407, [6, 10, 7], '{2:d}% Chance to cast Level {0:d} Skill<{1:d}> when struck'),
    PropertyDef(441, [7], 'Extra resistance from temporary resistance potions +{:d}%'),
    PropertyDef(443, [15], '+{:d} Extra duration (in frames) to all resistance potions'),
    PropertyDef(444, [15], '+{:d} Extra duration (in frames) to stamina potions'),
    PropertyDef(446, [9], 'Stamina Bonus {:d}%', offsets=[60]),
    PropertyDef(449, [7], 'bonus healing from normal rejuvination potions {:d}%'),
    PropertyDef(451, [4], 'Boosts the effectiveness of mana potions by x {:d}'),
    PropertyDef(465, [9], 'Boosts Double Throw Damage by {:d}%'),
    PropertyDef(471, [9], 'Boosts damage of Hireling Skills by {:d}%'),
    PropertyDef(479, [5], '+{:d} extra Potions launched from Potion Launcher skill'),
    PropertyDef(495, [6], '+{:d}/?? Min/Max Fire Damage (Increases with kills)[?]'),
    PropertyDef(502, [15], '+{:d} Extra duration (in frames) to RIP Potions'),
    PropertyDef(505, [15], '+{:d} Extra duration (in frames) to portable shrines'),
    PropertyDef(508, [12], 'Boosts Summon Damage by {:d}%'),
]}  # yapf: disable

# _PROPERTIES = {}
_LIST_TERMINATOR = 0x1ff

MISSING_PROPERTY_IDS = collections.Counter()


class PropertyList(object):
    def __init__(self, properties=None, terminator=None):
        self._properties = _PROPERTIES if properties is None else properties
        self._terminator = _LIST_TERMINATOR if terminator is None else terminator

    def from_bits(self, bits, **kwargs):
        position = 0
        properties = []
        terminated = False
        while True:
            prop_id, advanced = Integer(9).from_bits(bits[position:])
            position += advanced
            if prop_id == self._terminator:
                terminated = True
                break
            try:
                prop_def = self._properties[prop_id]
            except KeyError:
                MISSING_PROPERTY_IDS[prop_id] += 1
                Logger.warn('Unknown property ID: "{}"', prop_id)
                position -= advanced
                break
            else:
                values, advanced = self._get_fields_schema(prop_def).from_bits(
                    bits[position:])
                position += advanced
                values = [values[i] for i in xrange(len(prop_def.field_sizes))]
                if prop_def.offsets is not None:
                    values = [v - prop_def.offsets[i]
                              for i, v in enumerate(values)]
                properties.append(Property(prop_def, values))

        return PropList(properties, terminated), position

    def to_bits(self, proplist, **kwargs):
        res = ''
        for prop in proplist.properties:
            res += Integer(9).to_bits(prop.definition.id)
            values = prop.values
            if prop.definition.offsets:
                values = [v + prop.definition.offsets[i]
                          for i, v in enumerate(values)]
            res += self._get_fields_schema(prop.definition).to_bits(
                {i: v
                 for i, v in enumerate(values)})
        if proplist.terminated:
            res += Integer(9).to_bits(self._terminator)
        return res

    @staticmethod
    def _get_fields_schema(prop_def):
        return BinarySchema((SchemaPiece(i, Integer(s))
                             for i, s in enumerate(prop_def.field_sizes)))
