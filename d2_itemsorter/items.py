#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import functools
import logging
import os
import pkg_resources

from .logger import Logger

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

ItemTypeInfo = collections.namedtuple('ItemTypeInfo', ['id', 'name', 'width',
                                                       'height'])


_FILES_WITH_DEFENSE = (
    'data/items/armor',
    'data/items/belt',
    'data/items/boot',
    'data/items/glove',
    'data/items/shield',
    'data/items/helm',
)  # yapf: disable


_FILES_WITH_DURABILITY = (
    'data/items/armor',
    'data/items/belt',
    'data/items/boot',
    'data/items/glove',
    'data/items/shield',
    'data/items/weapon',
    'data/items/helm',
)  # yapf: disable


_FILES_WITH_QUANTITY = (
    'data/items/stack',
)  # yapf: disable

_LOADED_ITEMS = None
_KNOWN_ITEM_TYPES = {}
_ITEMS_WITH_DEFENSE = set()
_ITEMS_WITH_DURABILITY = set()
_ITEMS_WITH_QUANTITY = set()


def _load_items(handle):
    headers = handle.readline().strip().split(",")
    for line in handle:
        values = dict(zip(headers, line.strip().split(',')))
        values['width'] = int(values['width'])
        values['height'] = int(values['height'])
        yield ItemTypeInfo(**values)


def _get_items_from_file_prefixes(items_by_file, prefixes):
    res = set()
    for prefix in prefixes:
        for fname, items in items_by_file.items():
            if fname.startswith(prefix):
                res.update(i.id for i in items)
    return res


def _load_all_items():
    global _LOADED_ITEMS  # pylint: disable=global-statement
    global _ITEMS_WITH_DEFENSE  # pylint: disable=global-statement
    global _ITEMS_WITH_DURABILITY  # pylint: disable=global-statement
    global _ITEMS_WITH_QUANTITY  # pylint: disable=global-statement
    global _KNOWN_ITEM_TYPES  # pylint: disable=global-statement
    if _LOADED_ITEMS is not None:
        return
    with Logger.add_level("Loading items"):
        _LOADED_ITEMS = __load_all_items()

        _ITEMS_WITH_DEFENSE = _get_items_from_file_prefixes(
            _LOADED_ITEMS, _FILES_WITH_DEFENSE)
        Logger.info(" - {} items have defense", len(_ITEMS_WITH_DEFENSE))
        _ITEMS_WITH_DURABILITY = _get_items_from_file_prefixes(
            _LOADED_ITEMS, _FILES_WITH_DURABILITY)
        Logger.info(" - {} items have durability", len(_ITEMS_WITH_DURABILITY))
        _ITEMS_WITH_QUANTITY = _get_items_from_file_prefixes(
            _LOADED_ITEMS, _FILES_WITH_QUANTITY)
        Logger.info(" - {} items have quantity", len(_ITEMS_WITH_QUANTITY))

        _KNOWN_ITEM_TYPES = {i.id: i
                             for v in _LOADED_ITEMS.values() for i in v}


def __load_all_items():
    items = {}
    for fname in pkg_resources.resource_listdir(__name__, 'data/items'):
        fullname = os.path.join('data/items/', fname)
        inpu = pkg_resources.resource_stream(__name__, fullname)
        Logger.info("Loading items from {}", fullname)
        items[fullname] = tuple(_load_items(inpu))
        Logger.info("Loaded {} items", len(items[fullname]))
    Logger.info("Total items: {}", sum(len(v) for v in items.values()))
    return items


MISSING_ITEM_TYPES = set()


def get_item_type_info(item_type):
    _load_all_items()
    try:
        return _KNOWN_ITEM_TYPES[item_type]
    except KeyError:
        MISSING_ITEM_TYPES.add(item_type)
        return ItemTypeInfo(item_type, '??????????', '?', '?')


def item_has_defense(item_type):
    _load_all_items()
    return item_type in _ITEMS_WITH_DEFENSE


def item_has_durability(item_type):
    _load_all_items()
    return item_type in _ITEMS_WITH_DURABILITY


def item_has_quantity(item_type):
    _load_all_items()
    return item_type in _ITEMS_WITH_QUANTITY


def _get_data_root(item):
    try:
        return item['item']
    except KeyError:
        return item


def item_position(item):
    data = _get_data_root(item)
    try:
        return (data['position_y'], data['position_x'])
    except KeyError:
        raise ValueError("Could not find position for item.")


NORMAL_QUALITY_ID = 2
MAGIC_QUALITY_ID = 4
SET_QUALITY_ID = 5
RARE_QUALITY_ID = 6
UNIQUE_QUALITY_ID = 7


QUALITY_NAMES = {
    1: 'Low Quality',
    2: 'Normal',
    3: 'High Quality',
    4: 'Magic',
    5: 'Set Item',
    6: 'Rare',
    7: 'Unique',
    8: 'Crafted',
}  # yapf: disable


def _keyerror_net(func):
    @functools.wraps(func)
    def new_func(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except KeyError as err:
            raise ValueError("Could not find {} for item".format(err))

    return new_func


class Item(object):
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        return self._data

    def _data_root(self):
        try:
            return self._data['item']
        except KeyError:
            return self._data

    @_keyerror_net
    def type(self):
        data = self._data_root()
        return data['item_type']

    @_keyerror_net
    def position(self):
        data = self._data_root()
        return (data['position_y'], data['position_x'])

    def extended_info(self):
        data = self._data_root()
        return data.get('extended_info', {})

    def quality_id(self):
        ext_info = self.extended_info()
        return ext_info.get('quality', NORMAL_QUALITY_ID)

    def quality(self):
        return QUALITY_NAMES[self.quality_id()]

    def is_soul(self):
        return self.type().strip().isdigit()

    def level(self):
        ext_info = self.extended_info()
        return ext_info['drop_level']

    def info(self):
        return get_item_type_info(self.type())

    def size(self):
        info = self.info()
        return (info.width, info.height)

    def magic_affixes(self):
        ext_info = self.extended_info()
        return (ext_info.get('magic_prefix'), ext_info.get('magic_suffix'), )
