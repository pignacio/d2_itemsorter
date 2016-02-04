#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import itertools
import logging
import os
import sys
import time

from pignacio_scripts.terminal import color
import click

from .items import (MISSING_ITEM_TYPES, UNIQUE_QUALITY_ID, Item,
                    get_item_type_info)
from .logger import Logger
from .pager import item_type_filter, ItemFilter
from .schema import SchemaPiece, Integer, Chars, BinarySchema, Until
from .utils import str_to_bits, bits_to_str

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_SHARED_STASH_HEADER = str_to_bits("\x53\x53\x53\x00\x30\x31")
_STASH_HEADER = str_to_bits("\x43\x53\x54\x4d\x30\x31")
_PAGE_HEADER = str_to_bits("\x53\x54\x00\x4a\x4d")
_ITEM_HEADER = str_to_bits("\x4a\x4d")

_GREEN_TICK = color.bright_green(u"[✓]")


def _show_stash(stash):
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
                    extended_info = item_data.get('extended_info')
                    if extended_info:
                        Logger.info("ExInfo: q:{} iLvl:{}",
                                    extended_info['quality'],
                                    extended_info['drop_level'])
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


_ITEM_FILTERS = [
    ItemFilter('uniques', filter=is_valid_unique, sort=sort_uniques),
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
                if item.type() == 'mbag':
                    print item_filter.name, item_filter.filter(item)
                if item_filter.filter(item):
                    extracted[item_filter.name].append(item)
                    break
            else:
                new_page_items.append(item_data)
        page['items'] = new_page_items
        page['item_count'] = len(new_page_items)

    for item_filter in filters:
        extracted[item_filter.name] = [item.data
                                       for item in item_filter.sort(extracted[
                                           item_filter.name])]

    return extracted


def _sort_items(items_by_filter, sort_order):
    sorted_items = []
    for page in sort_order:
        sorted_items.append([])
        for row in page:
            items = [items_by_filter.get(row_piece, []) for row_piece in row]
            sorted_items[-1].append(list(itertools.chain(*items)))
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

        binary_str = str_to_bits(str_contents)

        parser = (BinarySchema(_SHARED_STASH_SCHEMA)
                  if binary_str.startswith(_SHARED_STASH_HEADER) else
                  BinarySchema(_PERSONAL_STASH_SCHEMA))
        stash = parser.decode(binary_str)

        _show_stash(stash)

        filters = _get_all_filters(_ITEMS_SORT_ORDER, _ITEM_FILTERS)
        extracted = _extract_items(stash['pages'], filters)

        _show_stash(stash)
        for item_type, items in sorted(extracted.items()):
            Logger.info("Extracted items '{}' ({})", item_type, len(items))

        from .pager import items_to_pages

        sorted_items = _sort_items(extracted, _ITEMS_SORT_ORDER)
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

        binary = parser.encode(stash)
        print len(binary)
        contents = bits_to_str(binary)

        if os.path.exists(handle.name) and patch:
            Logger.info('Patching: {}', handle.name)
            with open(handle.name, 'wb') as fout:
                fout.write(contents)

        with open("/tmp/test.d2x", "w") as fout:
            Logger.info('Writing to: /tmp/test.d2x', handle.name)
            fout.write(contents)


_EXTENDED_ITEM_SCHEMA = [
    SchemaPiece('gem_count', Integer(3)),
    SchemaPiece('guid', 32),
    SchemaPiece('drop_level', Integer(7)),
    SchemaPiece('quality', Integer(4)),
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
    SchemaPiece('_unk4', 26),
    SchemaPiece('position_x', Integer(4)),
    SchemaPiece('position_y', Integer(4)),
    SchemaPiece('_unk5', 3),
    SchemaPiece('item_type', Chars(4)),
    SchemaPiece(
        'extended_info',
        BinarySchema(_EXTENDED_ITEM_SCHEMA),
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
def parse(filename, debug, patch):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)
    logging.debug("PAGE: %s, %s", _PAGE_HEADER, bits_to_str(_PAGE_HEADER))
    logging.debug("ITEM: %s, %s", _ITEM_HEADER, bits_to_str(_ITEM_HEADER))
    _process_handle(filename, patch=patch)

    if MISSING_ITEM_TYPES:
        print "Missing item types:", repr(sorted(MISSING_ITEM_TYPES))
