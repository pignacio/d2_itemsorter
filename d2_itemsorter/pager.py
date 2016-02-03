#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

from pignacio_scripts.namedtuple import namedtuple_with_defaults

from .items import get_item_type_info, item_quality_id

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


def rows_to_pages(rows):
    pages = [[]]
    current_x = current_y = next_y = 0
    for row in rows:
        for item in row:
            info = get_item_type_info(item['item']['item_type'])
            if info.width != '?':
                width, height = info.width, info.height
            else:
                width, height = 2, 4
            if current_x + width > _PAGE_WIDTH:
                current_x = 0
                current_y = next_y
            if current_y + height > _PAGE_HEIGHT:
                pages.append([])
                current_x = current_y = next_y = 0
            item['item']['position_x'] = current_x
            item['item']['position_y'] = current_y
            pages[-1].append(item)
            current_x += width
            next_y = max(next_y, current_y + height)
        current_x = 0
        current_y = next_y
    return pages


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

    def insert(self, item):
        width, height = self._get_dimensions(item)
        if self._current_x + width > _PAGE_WIDTH:
            self.new_row()
        if self._current_y + height > _PAGE_HEIGHT:
            self.new_page()
        item['item']['position_x'] = self._current_x
        item['item']['position_y'] = self._current_y
        self._pages[-1].append(item)
        self._current_x += width
        self._next_y = max(self._next_y, self._current_y + height)

    @staticmethod
    def _get_dimensions(item):
        info = get_item_type_info(item['item']['item_type'])
        if info.width != '?':
            return info.width, info.height
        else:
            return 2, 4


def items_to_pages(sorted_items):
    pager = Pager()

    for page in sorted_items:
        for row in page:
            for item in row:
                pager.insert(item)
            pager.new_row()
        pager.new_page()
    return pager.pages
