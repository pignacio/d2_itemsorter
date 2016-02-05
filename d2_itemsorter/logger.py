#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import datetime

from pignacio_scripts.terminal import color


class Logger(object):
    _INDENT = 2
    level = 0

    class _Indenter(object):  # pylint: disable=too-few-public-methods
        def __enter__(self):
            Logger.level += 1

        def __exit__(self, *args, **kwargs):
            Logger.level -= 1

    @classmethod
    def info(cls, format_str, *args, **kwargs):
        return cls._log(format_str, *args, **kwargs)

    @classmethod
    def warn(cls, format_str, *args, **kwargs):
        format_str = color.bright_yellow(u"[?] " + format_str)
        return cls._log(format_str, *args, **kwargs)

    @classmethod
    def error(cls, format_str, *args, **kwargs):
        format_str = color.bright_red(u"[!!!] " + format_str)
        return cls._log(format_str, *args, **kwargs)

    @classmethod
    def _indent(cls):
        return " " * cls.level * cls._INDENT

    @classmethod
    def _log(cls, format_str, *args, **kwargs):
        log_line = u"[{}] {}{}".format(datetime.datetime.now(), cls._indent(),
                                       format_str.format(*args, **kwargs))
        print log_line.replace('\n', '\n' + cls._indent()).encode('utf-8')

    @classmethod
    def add_level(cls, *args, **kwargs):
        if args:
            format_str, nargs = args[0], args[1:]
            cls._log(color.blue(format_str), *nargs, **kwargs)
        return cls._Indenter()
