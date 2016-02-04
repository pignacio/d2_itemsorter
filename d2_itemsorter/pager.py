#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

from pignacio_scripts.namedtuple import namedtuple_with_defaults

from .items import Item

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_PAGE_WIDTH = 10
_PAGE_HEIGHT = 10


def default_sort(items):
    return sorted(items, key=lambda i: -i.quality_id())


ItemFilter = namedtuple_with_defaults('ItemFilter',
                                      ['name', 'filter', 'sort'],
                                      defaults={'sort': default_sort})


def item_type_filter(item_type):
    return ItemFilter(name=item_type, filter=lambda i: i.type() == item_type)


def items_to_rows(items):
    rows = collections.defaultdict(list)
    for item in items:
        item_type = item['item']['item_type']
        rows[item_type].append(item)

    return [row for _id, row in sorted(rows.items())]


class Pager(object):
    def __init__(self):
        self._pages = [[]]
        self._current_x = 0
        self._current_y = 0
        self._next_y = 0

    def new_page(self):
        self._pages.append([])
        self._current_x = 0
        self._current_y = 0
        self._next_y = 0

    def new_row(self):
        self._current_x = 0
        self._current_y = self._next_y

    @property
    def pages(self):
        return self._pages

    def insert(self, item_data):
        width, height = self._get_dimensions(item_data)
        if self._current_x + width > _PAGE_WIDTH:
            self.new_row()
        if self._current_y + height > _PAGE_HEIGHT:
            self.new_page()
        item_data['item']['position_x'] = self._current_x
        item_data['item']['position_y'] = self._current_y
        self._pages[-1].append(item_data)
        self._current_x += width
        self._next_y = max(self._next_y, self._current_y + height)

    @staticmethod
    def _get_dimensions(item_data):
        width, height = Item(item_data).size()
        if width == '?':
            return 2, 4
        return width, height


def items_to_pages(sorted_items):
    pager = Pager()

    for page in sorted_items:
        for row in page:
            for item in row:
                pager.insert(item)
            pager.new_row()
        pager.new_page()
    return pager.pages
