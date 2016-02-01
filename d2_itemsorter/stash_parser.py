#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import logging
import sys

from pignacio_scripts.terminal import color
import click

from .items import get_item_type_info, item_position, MISSING_ITEM_TYPES
from .logger import Logger
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
            for item_no, item in enumerate(sorted(page['items'],
                                                  key=item_position)):
                item_data = item['item']
                gems = item['gems']
                item_type = item_data['item_type']
                item_info = get_item_type_info(item_type)
                data = "{d.id} = {d.name} ({d.width}x{d.height})".format(
                    d=item_info)
                Logger.info("Item {}/{}: [{},{}] - {}".format(
                    item_no + 1, page['item_count'], item_data[
                        'position_x'], item_data['position_y'], data))
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


def _process_handle(handle):
    with Logger.add_level("Reading from '{}'", handle.name):
        str_contents = handle.read()
        Logger.info("Size: {} bytes", len(str_contents))

        binary_str = str_to_bits(str_contents)

        parser = (BinarySchema(_SHARED_STASH_SCHEMA)
                  if binary_str.startswith(_SHARED_STASH_HEADER) else
                  BinarySchema(_PERSONAL_STASH_SCHEMA))
        parsed = parser.decode(binary_str)

        _show_stash(parsed)
        all_items = list(_get_all_items_from_stash(parsed))

        from .pager import items_to_rows, rows_to_pages
        rows = items_to_rows(all_items)
        pages = rows_to_pages(rows)
        pages = [{
            'header': bits_to_str(_PAGE_HEADER),
            'item_count': len(p),
            'items': p,
        } for p in pages]

        parsed['page_count'] = len(pages)
        parsed['pages'] = pages

        _show_stash(parsed)

        binary = parser.encode(parsed)
        print len(binary)
        with open("/tmp/test.d2x", "w") as fout:
            fout.write(bits_to_str(binary))


_EXTENDED_ITEM_SCHEMA = [
    SchemaPiece('gem_count', Integer(3)),
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
@click.option('--debug', default=False, help='Turn on debug mode')
def parse(filename, debug):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=level)
    logging.debug("PAGE: %s, %s", _PAGE_HEADER, bits_to_str(_PAGE_HEADER))
    logging.debug("ITEM: %s, %s", _ITEM_HEADER, bits_to_str(_ITEM_HEADER))
    _process_handle(filename)

    if MISSING_ITEM_TYPES:
        print "Missing item types:", repr(sorted(MISSING_ITEM_TYPES))
