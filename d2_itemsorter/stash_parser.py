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
from .utils import bits_to_int

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

_COUNTERS = collections.defaultdict(collections.Counter)

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


class ParseError(Exception):
    pass


class ContentIter(object):
    def __init__(self, contents):
        self._contents = contents
        self._position = 0

    def peek(self, size):
        if size <= 0:
            raise ValueError("Number of bytes must be positive")
        return self._contents[self._position:self._position + size]

    def pop(self, size):
        res = self.peek(size)
        if size > 0 and not res:
            raise ParseError("EOF!")
        self._position += len(res)
        return res

    def starts_with(self, prefix):
        if isinstance(prefix, int):
            prefix = [prefix]
        return self.peek(len(prefix)) == prefix

    def remaining(self):
        return len(self._contents) - self._position


class Parser(object):
    def __init__(self, contents):
        self._contents = contents

    @property
    def contents(self):
        return self._contents

    def pop_expect(self, label, expected):
        size = len(expected)
        res = self._contents.pop(size)
        if res != expected:
            Logger.error(u"Invalid {}: {}. Expected {}", label,
                         _bytes_to_hex(res), _bytes_to_hex(expected))
        else:
            Logger.info(u"{}: {} {}", label, _bytes_to_hex(res), _GREEN_TICK)

    def pop(self, label, size):
        res = self._contents.pop(size)
        Logger.info(u"{}: {}", label, _bytes_to_hex(res))
        return res

    def pop_int(self, label, size, expected=None):
        byte_values = self._contents.pop(size)
        res = _parse_int(byte_values)
        if expected is not None:
            if res != expected:
                Logger.error(u"{}: {} (Expected {})", label, res, expected)
            else:
                Logger.info(u"{}: {} = {} {}", label,
                            _bytes_to_hex(byte_values), res, _GREEN_TICK)
        else:
            Logger.info(u"{}: {} = {}", label, _bytes_to_hex(byte_values), res)
        return res


def _process_filename(fname):
    if fname == '-':
        _process_handle(sys.stdin, "<STDIN>")
    else:
        with open(fname) as handle:
            _process_handle(handle, fname)


def _parse_int(int_bytes):
    return sum(b * 256**i for i, b in enumerate(int_bytes))


def _pop_int(contents, label, nbytes, expected=None):
    byte_values = contents.pop(nbytes)
    int_value = _parse_int(byte_values)
    Logger.info("{}: {} = {}", label, _bytes_to_hex(byte_values), int_value)
    if expected is not None and int_value != expected:
        Logger.error("Invalid value for {}: {} (Expected {})", label,
                     int_value, expected)
    return int_value


def _process_handle(handle, label):
    with Logger.add_level("Reading from '{}'", label):
        str_contents = handle.read()
        byte_contents = [ord(c) for c in str_contents]
        Logger.info("Size: {} bytes", len(byte_contents))
        # contents = ContentIter(byte_contents)
        # parser = Parser(contents)
        # _parse_stash(parser)
        binary_str = "".join(_value_to_bits(x)[::-1] for x in byte_contents)

        shared_header = "".join(_value_to_bits(x)[::-1]
                                for x in _SHARED_STASH_HEADER)
        parser = (BinarySchema(_SHARED_STASH_SCHEMA)
                  if binary_str.startswith(shared_header) else
                  BinarySchema(_PERSONAL_STASH_SCHEMA))
        parsed = parser.decode(binary_str)
        print json.dumps(parsed, indent=1)
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
        print json.dumps(parsed, indent=1)
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


def _parse_stash(parser):
    if parser.contents.starts_with(_SHARED_STASH_HEADER):
        parser.pop_expect("Shared stash header", _SHARED_STASH_HEADER)
    else:
        parser.pop_expect("Stash header", _STASH_HEADER)
        parser.pop_int("Unknown value", 4, expected=0)
    page_count = parser.pop_int("Page count", 4)

    for page_no in xrange(1, page_count + 1):
        with Logger.add_level("Page No {}/{}", page_no, page_count):
            _parse_page(parser)

    remaining = parser.contents.remaining()
    if remaining:
        Logger.warn("Remaining bytes: {}", remaining)
        Logger.warn("{}", _bytes_to_hex(parser.contents.pop(remaining)))


def _parse_page(parser):
    parser.pop_expect("Page header", _PAGE_HEADER)
    item_count = parser.pop_int("Item count", 2)
    for item_no in xrange(1, item_count + 1):
        with Logger.add_level("Item No {}/{}", item_no, item_count):
            _parse_item(parser)


def _value_to_bits(val, padding=None, size=None):
    if val < 0:
        raise ValueError("Value must be positive: {}".format(val))
    if size is not None:
        if val >= 2**size:
            raise ValueError("Value does not fit in {} bits: {}".format(size,
                                                                        val))
        padding = size
    elif padding is None:
        padding = 8

    res = bin(val)[2:]
    missing_padding = -len(res) % padding
    res = '0' * missing_padding + res
    return res


def _bits_to_value(bits):
    if not (isinstance(bits, basestring) and bits and all(b in ('0',
                                                                '1', )
                                                          for b in bits)):
        raise ValueError("bits must be a non-empty string of 0s an 1s")
    return eval('0b' + bits)  # pylint: disable=eval-used


class BinaryData(object):
    def __init__(self, content_bytes):
        self._data = "".join(_value_to_bits(x)
                             for x in reversed(content_bytes))

    def get_int_at(self, pos, size):
        binary = self._data[-pos - size:-pos]
        value = _bits_to_value(binary)
        return value

    def get_flag_at(self, pos, size=1):
        return self.get_int_at(pos, size) > 0


def _parse_item(parser):
    parser.pop_expect("Item header", _ITEM_HEADER)
    item_data = []
    while parser.contents.remaining() and not (
            parser.contents.starts_with(_ITEM_HEADER) or
            parser.contents.starts_with(_PAGE_HEADER)):
        item_data.extend(parser.contents.pop(1))
    Logger.info("Item data: {}", _bytes_to_hex(item_data))

    item_data = _ITEM_HEADER + item_data
    binary_data = "".join(_value_to_bits(x)[::-1] for x in item_data)
    schema = BinarySchema(_ITEM_SCHEMA)
    parsed = schema.decode(binary_data)
    encoded = schema.encode(parsed)
    if not binary_data == encoded:
        Logger.error("decode/encode failed!")
        Logger.error("Original: {}", binary_data)
        Logger.error("Encoded : {}", encoded)

    with Logger.add_level('Parsed:'):
        buf = StringIO(u'')
        json.dump(parsed, buf, indent=1)
        Logger.info('{}', buf.getvalue())

    parsed = parsed['item']
    Logger.info("Is identified: {}", parsed['identified'])
    Logger.info("Is socketed: {}", parsed['socketed'])
    Logger.info("Is simple: {}", parsed['simple'])
    Logger.info("Is ethereal: {}", parsed['ethereal'])

    item_type = parsed['item_type']
    _COUNTERS[0][item_type] += 1
    try:
        item_type_data = _KNOWN_ITEM_TYPES[item_type]
    except KeyError:
        Logger.warn("Item type: '{}'. I do not know what this is", item_type)
        _MISSING_ITEM_TYPES.add(item_type)
    else:
        Logger.info(u"Item type: {d.name} ({d.width}x{d.height}) ({}) {}",
                    item_type,
                    _GREEN_TICK,
                    d=item_type_data)

    Logger.info("Position = ({}, {})", parsed['position_x'],
                parsed['position_y'])

    if not parsed['simple']:
        gem_count = parsed['extended_info']['gem_count']
        Logger.info("Inserted gems: {}", gem_count)
        for gem_no in xrange(1, gem_count + 1):
            with Logger.add_level("Gem No {}/{}", gem_no, gem_count):
                pass  #_parse_item(parser)


_EXTENDED_ITEM_SCHEMA = [
    SchemaPiece('gem_count', Integer(3)),
]  # yapf: disable


_ITEM_STOP_PATTERNS = [
    "".join(_value_to_bits(x)[::-1]
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
#     SchemaPiece('has_rand', Integer(4)),
#     SchemaPiece('rand_vals', Nothing(96), condition='has_rand'),
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

    for i, c in sorted(_COUNTERS.items()):
        import pprint
        pprint.pprint((i, c.most_common()))

    if _MISSING_ITEM_TYPES:
        print "Missing item types:", repr(sorted(_MISSING_ITEM_TYPES))


if __name__ == "__main__":
    main()
