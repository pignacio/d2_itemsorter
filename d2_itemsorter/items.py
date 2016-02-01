#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging
import os
import pkg_resources

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
    items = {}
    for fname in pkg_resources.resource_listdir(__name__, 'data/items'):
        fullname = os.path.join('data/items/', fname)
        inpu = pkg_resources.resource_stream(__name__, fullname)
        for item in _load_items(inpu):
            items[item.id] = item
    return items


_KNOWN_ITEM_TYPES = _load_all_items()

MISSING_ITEM_TYPES = set()


def get_item_type_info(item_type):
    try:
        return _KNOWN_ITEM_TYPES[item_type]
    except KeyError:
        MISSING_ITEM_TYPES.add(item_type)
        return ItemTypeInfo(item_type, '??????????', '?', '?')


def item_position(item):
    try:
        return (item['position_y'], item['position_x'])
    except KeyError:
        try:
            subitem = item['item']
        except KeyError:
            raise ValueError("Could not find position for item.")
        else:
            return item_position(subitem)
