#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

from StringIO import StringIO
import collections
import json
import logging
import sys

from pignacio_scripts.terminal import color

from .logger import Logger
from .schema import SchemaPiece, Integer, Chars, BinarySchema, Until
from .utils import bits_to_int, int_to_bits

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def _bytes_to_hex(bytes_):
    return "[{}]".format(" ".join(hex(b) for b in bytes_))


def _values_to_bytes_array(*values):
    all_values = []
    for value in values:
        value_bytes = []
        if value == 0:
            value_bytes = [0]
        else:
            while value:
                value, value_byte = divmod(value, 256)
                value_bytes.append(value_byte)
        all_values.extend(reversed(value_bytes))
    return all_values


_SHARED_STASH_HEADER = _values_to_bytes_array(0x5353, 0x5300, 0x3031)
_STASH_HEADER = _values_to_bytes_array(0x4353, 0x544d, 0x3031)
_PAGE_HEADER = _values_to_bytes_array(0x535400, 0x4a, 0x4d)
_ITEM_HEADER = _values_to_bytes_array(0x4a, 0x4d)

ItemTypeInfo = collections.namedtuple('ItemTypeInfo', ['id', 'name', 'width',
                                                       'height'])


def _load_items(fname):
    with open(fname) as fin:
        headers = fin.readline().strip().split(",")
        for line in fin:
            values = dict(zip(headers, line.strip().split(',')))
            values['width'] = int(values['width'])
            values['height'] = int(values['height'])
            yield ItemTypeInfo(**values)

_KNOWN_ITEM_TYPES = {d.id: d for d in _load_items('items.csv')}

_MISSING_ITEM_TYPES = set()

_GREEN_TICK = color.bright_green(u"[✓]")


def _get_item_type_info(item_type):
    try:
        return _KNOWN_ITEM_TYPES[item_type]
    except KeyError:
        _MISSING_ITEM_TYPES.add(item_type)
        return ItemTypeInfo(item_type, '??????????', '?', '?')


def _process_filename(fname):
    if fname == '-':
        _process_handle(sys.stdin, "<STDIN>")
    else:
        with open(fname) as handle:
            _process_handle(handle, fname)


def _process_handle(handle, label):
    with Logger.add_level("Reading from '{}'", label):
        str_contents = handle.read()
        byte_contents = [ord(c) for c in str_contents]
        Logger.info("Size: {} bytes", len(byte_contents))
        # contents = ContentIter(byte_contents)
        # parser = Parser(contents)
        # _parse_stash(parser)
        binary_str = "".join(int_to_bits(x)[::-1] for x in byte_contents)

        shared_header = "".join(int_to_bits(x)[::-1]
                                for x in _SHARED_STASH_HEADER)
        parser = (BinarySchema(_SHARED_STASH_SCHEMA)
                  if binary_str.startswith(shared_header) else
                  BinarySchema(_PERSONAL_STASH_SCHEMA))
        parsed = parser.decode(binary_str)
        Logger.info("Found {} pages", parsed['page_count'])
        all_items = []
        for page_no, page in enumerate(parsed['pages']):
            with Logger.add_level("Page {}/{}", page_no + 1,
                                  parsed['page_count']):
                Logger.info("Item count: {}", page['item_count'])
                for item_no, item in enumerate(sorted(
                        page['items'],
                        key=
                        lambda i: (i['item']['position_y'], i['item']['position_x']))):
                    all_items.append(item)
                    item_data = item['item']
                    gems = item['gems']
                    item_type = item_data['item_type']
                    item_info = _get_item_type_info(item_type)
                    data = "{d.id} = {d.name} ({d.width}x{d.height})".format(
                        d=item_info)
                    Logger.info("Item {}/{}: [{},{}] - {}".format(
                        item_no + 1, page['item_count'], item_data[
                            'position_x'], item_data['position_y'], data))
                    if gems:
                        with Logger.add_level('Has {} gems', len(gems)):
                            for gem_no, gem in enumerate(gems):
                                gem_type = gem['item_type']
                                gem_info = _get_item_type_info(gem_type)
                                Logger.info(
                                    "Gem {}/{}: {d.id} = {d.name} ({d.width}x{d.height})",
                                    gem_no + 1,
                                    len(gem),
                                    d=gem_info)

        from .pager import items_to_rows, rows_to_pages
        rows = items_to_rows(all_items)
        pages = rows_to_pages(rows, _KNOWN_ITEM_TYPES)
        pages = [{
            'header': [chr(c) for c in _PAGE_HEADER],
            'item_count': len(p),
            'items': p,
        } for p in pages]

        parsed['page_count'] = len(pages)
        parsed['pages'] = pages

        Logger.info("Post sort")
        for page_no, page in enumerate(parsed['pages']):
            with Logger.add_level("Page {}/{}", page_no + 1,
                                  parsed['page_count']):
                Logger.info("Item count: {}", page['item_count'])
                for item_no, item in enumerate(sorted(
                        page['items'],
                        key=
                        lambda i: (i['item']['position_y'], i['item']['position_x']))):
                    item_data = item['item']
                    gems = item['gems']
                    item_type = item_data['item_type']
                    item_info = _get_item_type_info(item_type)
                    data = "{d.id} = {d.name} ({d.width}x{d.height})".format(
                        d=item_info)
                    Logger.info("Item {}/{}: [{},{}] - {}".format(
                        item_no + 1, page['item_count'], item_data[
                            'position_x'], item_data['position_y'], data))
                    if gems:
                        with Logger.add_level('Has {} gems', len(gems)):
                            for gem_no, gem in enumerate(gems):
                                gem_type = gem['item_type']
                                gem_info = _get_item_type_info(gem_type)
                                Logger.info(
                                    "Gem {}/{}: {d.id} = {d.name} ({d.width}x{d.height})",
                                    gem_no + 1,
                                    len(gem),
                                    d=gem_info)
        binary = parser.encode(parsed)
        print binary
        print len(binary)
        mybytes = [bits_to_int(binary[s:s+8][::-1]) for s in xrange(0, len(binary), 8)]
        chars = [chr(b) for b in mybytes]
        with open("test.d2x", "w") as fout:
            fout.write("".join(chars))


_EXTENDED_ITEM_SCHEMA = [
    SchemaPiece('gem_count', Integer(3)),
]  # yapf: disable


_ITEM_STOP_PATTERNS = [
    "".join(int_to_bits(x)[::-1]
            for x in pat) for pat in [_PAGE_HEADER, _ITEM_HEADER]
]


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
    SchemaPiece('tail', Until(_ITEM_STOP_PATTERNS))
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


def main():
    if len(sys.argv) == 1:
        # _process_handle(sys.stdin, '<STDIN>')
        _process_filename('Aleeria06.d2x')
    else:
        for fname in sys.argv[1:]:
            _process_filename(fname)

    if _MISSING_ITEM_TYPES:
        print "Missing item types:", repr(sorted(_MISSING_ITEM_TYPES))
