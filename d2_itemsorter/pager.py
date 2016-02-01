#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import collections
import logging

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

_PAGE_WIDTH = 10
_PAGE_HEIGHT = 10


def items_to_rows(items):
    rows = collections.defaultdict(list)
    for item in items:
        item_type = item['item']['item_type']
        rows[item_type].append(item)

    return [row for _id, row in sorted(rows.items())]


def rows_to_pages(rows, item_infos):
    pages = [[]]
    current_x = current_y = next_y = 0
    for row in rows:
        for item in row:
            info = item_infos[item['item']['item_type']]
            if current_x + info.width > _PAGE_WIDTH:
                current_x = 0
                current_y = next_y
            if current_y + info.height > _PAGE_HEIGHT:
                pages.append([])
                current_x = current_y = next_y = 0
            item['item']['position_x'] = current_x
            item['item']['position_y'] = current_y
            pages[-1].append(item)
            current_x += info.width
            next_y = max(next_y, current_y + info.height)
        current_x = 0
        current_y = next_y
    return pages
