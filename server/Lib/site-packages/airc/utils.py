"""
    Utility functions and classes for AIRC
"""

import re
import time
import logging

from .errors import *


__all__ = ("Cooldown", "LineBuffer", "SortedHandler", "IRCPrefix", "insort")


log = logging.getLogger("airc.utils")


class Cooldown:

    __slots__ = ("per", "time", "name", "start", "count")

    def __init__(self, per, time, name=""):
        self.per = per
        self.time = time
        self.name = name
        self.start = None
        self.count = 0

    def set_per(self, per):
        self.per = per

    def set_time(self, time):
        self.time = time

    def can_run(self):
        now = time.time()
        if self.start is None:
            self.start = now
            self.count = 1
            return 0
        elif now > self.start + self.time:
            self.start = now
            self.count = 1
            return 0
        elif self.count < self.per:
            self.count += 1
            return 0
        else:
            remaining = (self.time + self.start) - self.start
            log.info(f"Overran cooldown, {remaining} seconds till it's over.")
            return remaining


class LineBuffer:

    __slots__ = ("data",)

    _line_sep = re.compile(b"\r?\n")

    def __init__(self):
        self.data = b''

    def feed(self, line):
        if isinstance(line, str):
            line = bytes(line, 'utf-8')
        self.data += line

    def lines(self):
        lines = self._line_sep.split(self.data)
        self.data = lines.pop()
        for line in lines:
            try:
                yield line.decode('utf-8', 'strict')
            except UnicodeDecodeError:
                raise AIRCError("Unknown websocket data encoding")

    def __iter__(self):
        return self.lines()

    def __len__(self):
        return len(self.data)


class SortedHandler:

    __slots__ = ("handler", "priority")

    def __init__(self, handler, priority):
        self.handler = handler
        self.priority = priority

    async def __call__(self, event):
        await self.handler(event)

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority


_irc_prefix_pattern = r"^(?:(?P<nick>\w+)!)?(?:(?P<user>\w+)@)?(?P<host>.+)"
_irc_prefix = re.compile(_irc_prefix_pattern)


class IRCPrefix(str):

    __slots__ = ("nick", "user", "host")

    def __new__(cls, prefix):
        if not isinstance(prefix, str):
            prefix = ""
        return super(IRCPrefix, cls).__new__(cls, prefix)

    def __init__(self, prefix):
        if not isinstance(prefix, str):
            prefix = ""
        super().__init__()
        if prefix != "":
            match = _irc_prefix.match(prefix)
            self.nick = match.group("nick")
            self.user = match.group("user")
            self.host = match.group("host")


def insort(li, o, lo=0, hi=None):
    if hi is None:
        hi = len(li)
    while lo < hi:
        middle = (lo + hi) // 2
        if o < li[middle]:
            hi = middle
        else:
            lo = middle + 1
    li.insert(lo, o)
