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


def _load_items(handle):
    headers = handle.readline().strip().split(",")
    for line in handle:
        values = dict(zip(headers, line.strip().split(',')))
        values['width'] = int(values['width'])
        values['height'] = int(values['height'])
        yield ItemTypeInfo(**values)


def _load_all_items():
    with Logger.add_level("Loading items"):
        return __load_all_items()


def __load_all_items():
    items = {}
    for fname in pkg_resources.resource_listdir(__name__, 'data/items'):
        fullname = os.path.join('data/items/', fname)
        inpu = pkg_resources.resource_stream(__name__, fullname)
        Logger.info("Loading items from {}", fullname)
        count = 0
        for item in _load_items(inpu):
            count += 1
            items[item.id] = item
        Logger.info("Loaded {} items", count)
    Logger.info("Total items: {}", len(items))
    return items


_KNOWN_ITEM_TYPES = _load_all_items()

MISSING_ITEM_TYPES = set()


def get_item_type_info(item_type):
    try:
        return _KNOWN_ITEM_TYPES[item_type]
    except KeyError:
        MISSING_ITEM_TYPES.add(item_type)
        return ItemTypeInfo(item_type, '??????????', '?', '?')


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
