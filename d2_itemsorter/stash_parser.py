#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import cProfile
import itertools
import logging
import os
import pstats
import sys
import time

from pignacio_scripts.terminal import color
import click

from .items import (MISSING_ITEM_TYPES, UNIQUE_QUALITY_ID, SET_QUALITY_ID,
                    Item, get_item_type_info, item_has_defense,
                    item_has_quantity, item_has_durability)
from .logger import Logger
from .pager import item_type_filter, ItemFilter, items_to_pages
from .props import PropertyList, MISSING_PROPERTY_IDS
from .schema import (SchemaPiece, Integer, Chars, BinarySchema, Until,
                     NullTerminatedChars)
from .utils import str_to_bits, bits_to_str

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_SHARED_STASH_HEADER = str_to_bits("\x53\x53\x53\x00\x30\x31")
_STASH_HEADER = str_to_bits("\x43\x53\x54\x4d\x30\x31")
_PAGE_HEADER = str_to_bits("\x53\x54\x00\x4a\x4d")
_ITEM_HEADER = str_to_bits("\x4a\x4d")

_GREEN_TICK = color.bright_green(u"[✓]")


def _show_stash(stash, show_extended=False):
    Logger.info("Has {} pages", stash['page_count'])
    for page_no, page in enumerate(stash['pages']):
        with Logger.add_level("Page {}/{}", page_no + 1, stash['page_count']):
            Logger.info("Item count: {}", page['item_count'])
            for item_no, item_data in enumerate(
                    sorted(page['items'],
                           key=lambda i: Item(i).position())):
                gems = item_data['gems']
                item = Item(item_data)
                item_info = item.info()
                data = "{d.id} = {d.name} ({d.width}x{d.height})".format(
                    d=item_info)
                Logger.info("Item {}/{}: {} - {} [{}]".format(
                    item_no + 1, page['item_count'], item.position(
                    ), data, item.quality()))
                with Logger.add_level():
                    extended_info = item.extended_info()
                    if show_extended and extended_info:
                        Logger.info("ExInfo: q:{} iLvl:{} setId:{}",
                                    extended_info['quality'],
                                    extended_info['drop_level'],
                                    extended_info.get('set_id'))
                    if gems:
                        with Logger.add_level('Has {} gems', len(gems)):
                            for gem_no, gem in enumerate(gems):
                                gem_type = gem['item_type']
                                gem_info = get_item_type_info(gem_type)
                                Logger.info(
                                    "Gem {}/{}: {d.id} = {d.name} ({d.width}x{d.height})",
                                    gem_no + 1,
                                    len(gem),
                                    d=gem_info)


def _get_all_items_from_stash(stash):
    for page in stash['pages']:
        for item in page['items']:
            yield item


_INVALID_UNIQUE_TYPES = {'mbag', 'mgat'}


def is_valid_unique(item):
    return (item.quality_id() == UNIQUE_QUALITY_ID and not item.is_soul() and
            not item.type() in _INVALID_UNIQUE_TYPES)


def sort_uniques(items):
    return sorted(items, key=lambda i: i.type())


def sort_by_level(items):
    return sorted(items, key=lambda i: i.level())


def is_valid_set_item(item):
    return item.quality_id() == SET_QUALITY_ID


def set_items_sort(items):
    return sorted(items, key=lambda i: i.extended_info()['set_id'])


_ITEM_FILTERS = [
    ItemFilter('uniques', filter=is_valid_unique, sort=sort_uniques),
    ItemFilter('sets', filter=is_valid_set_item, sort=set_items_sort),
    ItemFilter('souls', filter=lambda i: i.is_soul(), sort=sort_by_level),
]  # yapf: disable


_ITEMS_SORT_ORDER = [
    [['rvsl'], ['rvs '], ['rvl ']],
    [['ept '], ['ep2 '], ['ep3 '], ['ep4 '], ['ep5 '], ['ep6 ']],
    [['cm1 '], ['cm2 '], ['cm3 ']],
    [['amu ']],
    [['rin ']],
    [['souls']],
    [
        ['gsb ', 'gfb ', 'gcb '],
        ['gsg ', 'gfg ', 'gcg '],
        ['gsr ', 'gfr ', 'gcr '],
        ['gsv ', 'gfv ', 'gcv '],
        ['gsw ', 'gfw ', 'gcw '],
        ['gsy ', 'gfy ', 'gcy '],
        ['skl ', 'skf ', 'skc '],
    ],
    [
        ['r{:02} '.format(i)] for i in xrange(1, 31)
    ],
    [['jew ']],
    [['trpg']],
    [['gld1'], ['gld2'], ['gld3'], ['gld4']],
    [['cb1 '], ['fuk '], ['egb '], ['spg '], ['tet ']],
    [['mbag']],
    [['mgat']],
    [['01d ']],
    [['ggr ']],
    [['m03 ', 'm04 ']],
    [['uniques']],
    [['sets']],
]  # yapf: disable


def _get_all_filters(sort_order, pre_filters):
    filters = []
    names = set()
    by_name = {f.name: f for f in pre_filters}
    for page in sort_order:
        for row in page:
            for row_piece in row:
                names.add(row_piece)
                if row_piece not in by_name:
                    item_filter = item_type_filter(row_piece)
                    filters.append(item_filter)
    return [f for f in pre_filters if f.name in names] + filters


def _get_all_sorted_item_types(sort_order):
    res = set()
    for page in sort_order:
        for row in page:
            for row_type in row:
                if row_type in res:
                    raise ValueError(
                        "Duplicate item type in sort order: {!r}".format(
                            row_type))
                res.add(row_type)
    return res


def _extract_items(pages, filters):
    extracted = collections.defaultdict(list)
    for page in pages:
        new_page_items = []
        for item_data in page['items']:
            item = Item(item_data)
            for item_filter in filters:
                if item_filter.filter(item):
                    extracted[item_filter.name].append(item)
                    break
            else:
                new_page_items.append(item_data)
        page['items'] = new_page_items
        page['item_count'] = len(new_page_items)

    for item_filter in filters:
        items = extracted[item_filter.name]
        items = item_filter.sort(items)
        if not (items and isinstance(items[0], (list, tuple))):
            items = (items,)
        extracted[item_filter.name] = [[item.data for item in item_row]
                                       for item_row in items]

    return extracted


def _sort_items(items_by_filter, sort_order):
    sorted_items = []
    for page in sort_order:
        sorted_items.append([])
        for row in page:
            sorted_items[-1].append([])
            for row_piece in row:
                items = items_by_filter.get(row_piece, [[]])
                for item_row in items:
                    sorted_items[-1][-1].extend(item_row)
                    if len(items) > 1 and sorted_items[-1][-1]:
                        sorted_items[-1].append([])
    return sorted_items


def _process_handle(handle, patch=False):
    with Logger.add_level("Reading from '{}'", handle.name):
        str_contents = handle.read()
        Logger.info("Size: {} bytes", len(str_contents))
        if os.path.exists(handle.name):
            fname, extension = os.path.basename(handle.name).rsplit(".", 1)
            backup_file = os.path.join("backups", "{}-{}.{}".format(
                fname, int(time.time()), extension))
            try:
                os.makedirs('backups')
            except OSError:
                pass
            Logger.info("Writing backup...")
            with open(backup_file, 'wb') as fout:
                fout.write(str_contents)
            Logger.info("Done writing backup")

        Logger.info('Converting to binary string')
        binary_str = str_to_bits(str_contents)

        Logger.info('Decoding...')
        parser = (BinarySchema(_SHARED_STASH_SCHEMA)
                  if binary_str.startswith(_SHARED_STASH_HEADER) else
                  BinarySchema(_PERSONAL_STASH_SCHEMA))
        stash = parser.decode(binary_str)
        Logger.info('Decoded')

        _show_stash(stash)

        filters = _get_all_filters(_ITEMS_SORT_ORDER, _ITEM_FILTERS)
        Logger.info('There are {} filter', len(filters))
        extracted = _extract_items(stash['pages'], filters)
        for item_type, items in sorted(extracted.items()):
            count = sum(len(r) for r in items)
            if count:
                Logger.info("Extracted items '{}' ({})", item_type, count)

        Logger.info("Sorting items")
        sorted_items = _sort_items(extracted, _ITEMS_SORT_ORDER)
        Logger.info("Paging items")
        pages = items_to_pages(sorted_items)

        empty_page = {
            'header': bits_to_str(_PAGE_HEADER),
            'item_count': 0,
            'items': [],
        }

        new_pages = [empty_page]
        new_pages.extend([p for p in stash['pages'] if p['items']])
        new_pages.append(empty_page)
        new_pages.extend([{
            'header': bits_to_str(_PAGE_HEADER),
            'item_count': len(p),
            'items': p,
        } for p in pages if p])

        stash['pages'] = new_pages
        stash['page_count'] = len(new_pages)

        _show_stash(stash)

        Logger.info("Encoding...")
        binary = parser.encode(stash)
        contents = bits_to_str(binary)
        Logger.info("Encoded. Size: {} ({} bits)", len(contents), len(binary))

        if os.path.exists(handle.name) and patch:
            Logger.info('Patching: {}', handle.name)
            with open(handle.name, 'wb') as fout:
                fout.write(contents)

        with open("/tmp/test.d2x", "w") as fout:
            Logger.info('Writing to: /tmp/test.d2x', handle.name)
            fout.write(contents)


_ITEMS_WITHOUT_PROPERTIES = set()


def _parent_type(values):
    return values[BinarySchema.PARENT_FIELD]['item_type']


def _parent_quality(values):
    return values[BinarySchema.PARENT_FIELD]['extended_info']['quality']


_SPECIFIC_ITEM_SCHEMA = [
    SchemaPiece(
        'defense',
        Integer(11),
        condition=lambda v: item_has_defense(_parent_type(v))),
    SchemaPiece(
        'max_durability',
        Integer(9),
        condition=lambda v: item_has_durability(_parent_type(v))),
    SchemaPiece(
        'current_durability',
        Integer(9),
        condition='max_durability'),
    SchemaPiece(
        'num_sockets',
        Integer(4),
        condition='..socketed'),
    SchemaPiece(
        'quantity',
        Integer(9),
        condition=lambda v: item_has_quantity(_parent_type(v))),
    SchemaPiece('has_set_props_1', Integer(1),
                condition=lambda v: _parent_quality(v) == 5),
    SchemaPiece('has_set_props_2', Integer(1),
                condition=lambda v: _parent_quality(v) == 5),
    SchemaPiece('has_set_props_3', Integer(1),
                condition=lambda v: _parent_quality(v) == 5),
    SchemaPiece('has_set_props_4', Integer(1),
                condition=lambda v: _parent_quality(v) == 5),
    SchemaPiece('has_set_props_5', Integer(1),
                condition=lambda v: _parent_quality(v) == 5),
    SchemaPiece('properties', PropertyList(),
                condition=lambda v: _parent_type(v) not in _ITEMS_WITHOUT_PROPERTIES),
    SchemaPiece('set_props_1', PropertyList(), condition='has_set_props_1'),
    SchemaPiece('set_props_2', PropertyList(), condition='has_set_props_2'),
    SchemaPiece('set_props_3', PropertyList(), condition='has_set_props_3'),
    SchemaPiece('set_props_4', PropertyList(), condition='has_set_props_4'),
    SchemaPiece('set_props_5', PropertyList(), condition='has_set_props_5'),
]  # yapf: disable

_EXTENDED_ITEM_SCHEMA = [
    SchemaPiece('gem_count', Integer(3)),
    SchemaPiece('guid', 32),
    SchemaPiece('drop_level', Integer(7)),
    SchemaPiece('quality', Integer(4)),
    SchemaPiece('has_gfx', Integer(1)),
    SchemaPiece('gfx', Integer(3), condition='has_gfx'),
    SchemaPiece('has_class_info', Integer(1)),
    SchemaPiece('class_info', Integer(11), condition='has_class_info'),
    SchemaPiece('lo_qual_type', Integer(3),
                condition=lambda v: v['quality'] == 1),
    SchemaPiece('hi_qual_type', Integer(3),
                condition=lambda v: v['quality'] == 3),
    SchemaPiece('magic_prefix', Integer(11),
                condition=lambda v: v['quality'] == 4),
    SchemaPiece('magic_suffix', Integer(11),
                condition=lambda v: v['quality'] == 4),
    SchemaPiece('set_id', Integer(12),
                condition=lambda v: v['quality'] == 5),
    SchemaPiece('rare_name_1', Integer(8),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('rare_name_2', Integer(8),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('has_prefix_1', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('prefix_1', Integer(11),
                condition='has_prefix_1'),
    SchemaPiece('has_suffix_1', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('suffix_1', Integer(11),
                condition='has_suffix_1'),
    SchemaPiece('has_prefix_2', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('prefix_2', Integer(11),
                condition='has_prefix_2'),
    SchemaPiece('has_suffix_2', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('suffix_2', Integer(11),
                condition='has_suffix_2'),
    SchemaPiece('has_prefix_3', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('prefix_3', Integer(11),
                condition='has_prefix_3'),
    SchemaPiece('has_suffix_3', Integer(1),
                condition=lambda v: v['quality'] in (6, 8,)),
    SchemaPiece('suffix_3', Integer(11),
                condition='has_suffix_3'),
    SchemaPiece('unique_id', Integer(12),
                condition=lambda v: v['quality'] == 7),
    SchemaPiece('runeword', Integer(16),
                condition='..has_runeword'),
    SchemaPiece('runeword', NullTerminatedChars(7),
                condition='..inscribed'),
]  # yapf: disable


_ITEM_DATA_SCHEMA = [
    SchemaPiece('header', Chars(2)),
    SchemaPiece('_unk1', 4),
    SchemaPiece('identified', Integer(1)),
    SchemaPiece('_unk2', 6),
    SchemaPiece('socketed', Integer(1)),
    SchemaPiece('_unk3', 9),
    SchemaPiece('simple', Integer(1)),
    SchemaPiece('ethereal', Integer(1)),
    SchemaPiece('_unk4', 1),
    SchemaPiece('inscribed', Integer(1)),
    SchemaPiece('_unk5', 1),
    SchemaPiece('has_runeword', Integer(1)),
    SchemaPiece('_unk6', 22),
    SchemaPiece('position_x', Integer(4)),
    SchemaPiece('position_y', Integer(4)),
    SchemaPiece('_unk7', 3),
    SchemaPiece('item_type', Chars(4)),
    SchemaPiece(
        'extended_info',
        BinarySchema(_EXTENDED_ITEM_SCHEMA),
        condition=lambda v: not v['simple']),
    SchemaPiece('has_random_pad', Integer(1)),
    SchemaPiece('random_pad', Integer(96), condition='has_random_pad'),
    SchemaPiece(
        'specific_info',
        BinarySchema(_SPECIFIC_ITEM_SCHEMA),
        condition=lambda v: not v['simple']),
    SchemaPiece('tail', Until([_PAGE_HEADER, _ITEM_HEADER]))
]  # yapf: disable


_ITEM_SCHEMA = [
    SchemaPiece('item', BinarySchema(_ITEM_DATA_SCHEMA)),
    SchemaPiece(
        'gems',
        BinarySchema(_ITEM_DATA_SCHEMA),
        multiple=lambda v: v['item'].get('extended_info', {}).get('gem_count', 0)),
]  # yapf: disable


_PAGE_SCHEMA = [
    SchemaPiece('header', Chars(5)),
    SchemaPiece('item_count', Integer(16)),
    SchemaPiece(
        'items',
        BinarySchema(_ITEM_SCHEMA),
        multiple=lambda v: v['item_count']),
]  # yapf: disable


_PERSONAL_STASH_SCHEMA = [
    SchemaPiece('header', Chars(6)),
    SchemaPiece('_unk1', 32),
    SchemaPiece('page_count', Integer(32)),
    SchemaPiece(
        'pages',
        BinarySchema(_PAGE_SCHEMA),
        multiple=lambda v: v['page_count']),
]  # yapf: disable


_SHARED_STASH_SCHEMA = [
    SchemaPiece('header', Chars(6)),
    SchemaPiece('page_count', Integer(32)),
    SchemaPiece(
        'pages',
        BinarySchema(_PAGE_SCHEMA),
        multiple=lambda v: v['page_count']),
]  # yapf: disable


@click.command()
@click.argument('filename', type=click.File('rb'))
@click.option('--debug', is_flag=True, help='Turn on debug mode')
@click.option('--patch', is_flag=True, help='Patch the file in place')
@click.option('--profile', is_flag=True, help='Profile the execution')
def parse(filename, debug, patch, profile):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)
    logging.debug("PAGE: %s, %s", _PAGE_HEADER, bits_to_str(_PAGE_HEADER))
    logging.debug("ITEM: %s, %s", _ITEM_HEADER, bits_to_str(_ITEM_HEADER))

    if profile:
        profiler = cProfile.Profile()
        profiler.enable()
    else:
        profiler = None

    _process_handle(filename, patch=patch)

    if profiler:
        profiler.disable()
        stats = pstats.Stats(profiler, stream=sys.stdout).sort_stats('cumulative')
        stats.print_stats()


    if MISSING_ITEM_TYPES:
        print "Missing item types:", repr(sorted(MISSING_ITEM_TYPES))

    if MISSING_PROPERTY_IDS:
        print "Missing property ids:", repr(sorted(MISSING_PROPERTY_IDS.items())), repr(MISSING_PROPERTY_IDS.most_common())

    print "Full parses?: ", _ITEM_PARSES
