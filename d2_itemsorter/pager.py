#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

from .items import get_item_type_info

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_PAGE_WIDTH = 10
_PAGE_HEIGHT = 10


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
