"""
    Server classes for the AIRC
"""


import re
import abc
import asyncio
import logging
import websockets

from .enums import ReplyCode, EventType
from .errors import *
from .events import Event
from .utils import insort, LineBuffer, SortedHandler, IRCPrefix


__all__ = ("Server", "DefaultServer")


log = logging.getLogger("airc.server")
_cap_subcommands = set('LS LIST REQ ACK NAK CLEAR END'.split())
_client_subcommands = set(_cap_subcommands) - {'NAK'}
_rfc_pattern = r"^(@(?P<tags>[^ ]*) )?(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)( *(?P<argument> .+))?"
_regexp_rfc = re.compile(_rfc_pattern)


# TODO: Move some of this to utils
def _handle_tags(tags):
    if tags is None:
        return {}
    tags = tags.lstrip("@")
    raw_tags = tags.split(";")
    tags = {}
    for raw_tag in raw_tags:
        name, val = raw_tag.split("=")
        if val == "":
            val = None
        tags[name] = val
    return tags


def _handle_args(args):
    args = args.lstrip()
    out_args = []
    rest = False
    tmp = ""
    for char in args:
        if rest:
            tmp += char
        elif char == " ":
            out_args.append(tmp)
            tmp = ""
        elif char == ":" and tmp == "":
            rest = True
        else:
            tmp += char
    if tmp:
        out_args.append(tmp)
    return out_args


def _handle_command(command):
    if not command.isnumeric():
        return EventType.PROTOCOL, command

    try:
        com = int(command)
        code = ReplyCode(com)

        if 0 <= com <= 399:
            type = EventType.REPLY
        elif 400 <= com <= 599:
            type = EventType.ERROR
        else:
            type = EventType.UNKNOWN

    except ValueError:
        return EventType.UNKNOWN, command

    return type, code.name


def _handle_prefix(prefix):
    if prefix is None:
        return None
    return IRCPrefix(prefix)


class Server:
    """
        Generic IRC connection. Subclassed by specific kinds of servers.
    """

    __slots__ = ("loop", "master", "handlers", "socket", "connected", "_uri")

    def __init__(self, uri, master=None, *, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.master = master

        self._uri = uri

        self.handlers = {}
        self.socket = None
        self.connected = False

    def add_global_handler(self, event, handler, priority=0):
        if self.master:
            self.master.add_global_handler(event, handler, priority)

    def remove_global_handler(self, event, handler):
        if self.master:
            self.master.remove_global_handler(event, handler)

    def add_handler(self, event, handler, priority=0):
        handler = SortedHandler(handler, priority)
        li = self.handlers.setdefault(event, [])
        insort(li, handler)

    def remove_handler(self, event, handler):
        handlers = self.handlers.get(event, [])
        for h in handlers:
            if h.handler == handler:
                handlers.remove(h)
                break

    async def _handle_event(self, event):
        if self.master:
            self.loop.create_task(self.master._handle_event(event))
        for handler in self.handlers.get("all_events", ()):
            try:
                await handler(event)
            except Exception as e:
                raise HandlerError(e)
        for handler in self.handlers.get(event.command, ()):
            try:
                await handler(event)
            except Exception as e:
                raise HandlerError(e)

    @abc.abstractmethod
    async def connect(self, name, password=""):
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def process_data(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def send_raw(self, data):
        raise NotImplementedError


class DefaultServer(Server):
    """
        The default server is a 'standard' IRC server, complying with the
        IRC specification
    """

    __slots__ = ("buffer", "_uri", "username", "password")

    def __init__(self, uri, master=None, *, loop=None):
        super().__init__(uri, master, loop=loop)
        self.buffer = LineBuffer()
        self.username = None
        self.password = None

    async def connect(self, username, password=""):
        self.username = username
        self.password = password

        self.socket = await websockets.connect(self._uri, ssl=None)
        self.connected = True

        if self.password:
            await self.pass_(self.password)
        await self.nick(self.username)
        await self.user(self.username, self.username)

    async def disconnect(self):
        await self.socket.close()
        self.socket = None
        self.connected = False

    # Methods for receiving data

    async def process_data(self):
        try:
            data = await self.socket.recv()
        except websockets.ConnectionClosed:
            await self.disconnect()
            raise
        if isinstance(data, str):
            data = bytes(data, 'utf-8')
        if chr(data[-1]) != "\n":
            data += b'\n'

        self.buffer.feed(data)

        for line in self.buffer:
            if not line:
                continue
            await self._process_line(line)

        return self

    async def _process_line(self, line):
        event = Event(self, EventType.CLIENT, "all_raw_events", [None, line])
        await self._handle_event(event)

        match = _regexp_rfc.match(line)

        type, command = _handle_command(match.group('command'))
        command = command.lower()

        args = _handle_args(match.group('argument'))

        tags = _handle_tags(match.group('tags'))

        prefix = _handle_prefix(match.group('prefix'))

        # Dispatch the actual specific event
        event = Event(self, type, command, args, prefix, tags)
        log.debug(event)
        await self._handle_event(event)

    # Methods for sending data

    async def send_raw(self, data):
        await self.socket.send(data)

    async def send_items(self, *items):
        await self.send_raw(' '.join(filter(None, items)))

    # Handlers to send individual commands

    # Server management

    async def pass_(self, password):
        await self.send_items("PASS", password)

    async def nick(self, nick):
        await self.send_items("NICK", nick)

    async def user(self, user, realname, mode=None):
        if mode is None:
            mode = "0"
        await self.send_items("USER", user, mode, "*", f":{realname}")

    async def oper(self, name, password):
        await self.send_items("OPER", name, password)

    async def mode(self, nick, mode, param=None):
        await self.send_items("MODE", nick, mode, param)

    async def service(self, nick, distribution, type, info):
        await self.send_items("SERVICE", nick, "*", distribution, type, "*", f":{info}")

    async def quit(self, message=None):
        if message is not None:
            message = f":{message}"
        await self.send_items("QUIT", message)
        await self.disconnect()

    async def squit(self, server, comment=None):
        if comment is not None:
            comment = f":{comment}"
        await self.send_items("SQUIT", server, comment)

    # Channel management

    async def join(self, channel, key=None):
        if isinstance(channel, list):
            if key is not None and not isinstance(key, list):
                raise TypeError("List of channels must use list of keys, if keys are provided")
            channel = ",".join(channel)
            if key is not None:
                key = ",".join(key)
        await self.send_items("JOIN", channel, key)

    async def part(self, channel, message=None):
        if isinstance(channel, list):
            channel = ",".join(channel)
        if message is not None:
            message = f":{message}"
        await self.send_items("PART", channel, message)

    async def topic(self, channel, topic=None):
        if topic is not None:
            topic = f":{topic}"
        await self.send_items("TOPIC", channel, topic)

    async def names(self, channel=None, target=None):
        if isinstance(channel, list):
            channel = ",".join(channel)
        await self.send_items("NAMES", channel, target)

    async def list(self, channel=None, target=None):
        if isinstance(channel, list):
            channel = ",".join(channel)
        await self.send_items("LIST", channel, target)

    async def invite(self, nick, channel):
        await self.send_items("INVITE", nick, channel)

    async def kick(self, channel, user, comment=None):
        if isinstance(channel, list):
            channel = ",".join(channel)
        if isinstance(user, list):
            user = ",".join(user)
        if comment is not None:
            comment = f":{comment}"
        await self.send_items("KICK", channel, user, comment)

    # Sending messages

    async def privmsg(self, target, text):
        text = f":{text}"
        await self.send_items("PRIVMSG", target, text)

    async def notice(self, target, text):
        text = f":{text}"
        await self.send_items("NOTICE", target, text)

    # Server queries

    async def motd(self, target=None):
        await self.send_items("MOTD", target)

    async def lusers(self, mask=None, target=None):
        await self.send_items("LUSERS", mask, target)

    async def version(self, target=None):
        await self.send_items("VERSION", target)

    async def stats(self, query=None, target=None):
        await self.send_items("STATS", query, target)

    async def links(self, mask=None, remote=None):
        await self.send_items("LINKS", remote, mask)

    async def time(self, target=None):
        await self.send_items("TIME", target)

    async def connect_(self, target, port, remote=None):
        await self.send_items("CONNECT", target, port, remote)

    async def trace(self, target=None):
        await self.send_items("TRACE", target)

    async def admin(self, target=None):
        await self.send_items("ADMIN", target)

    async def info(self, target=None):
        await self.send_items("INFO", target)

    # Service queries

    async def servlist(self, mask=None, type=None):
        await self.send_items("SERVLIST", mask, type)

    async def squery(self, name, text):
        text = f":{text}"
        await self.send_items(name, text)

    # User queries

    async def who(self, mask=None, ops_only=False):
        if mask is None:
            mask = "0"
        if ops_only is True:
            mask += " o"
        await self.send_items("WHO", mask)

    async def whois(self, mask, target=None):
        if isinstance(mask, list):
            mask = ",".join(mask)
        await self.send_items("WHOIS", target, mask)

    async def whowas(self, nick, count=None, target=None):
        if isinstance(nick, list):
            nick = ",".join(nick)
        await self.send_items("WHOWAS", nick, count, target)

    # Miscellaneous messages

    async def kill(self, nick, comment):
        comment = f":{comment}"
        await self.send_items("KILL", nick, comment)

    async def ping(self, serv1, serv2=None):
        await self.send_items("PING", serv1, serv2)

    async def pong(self, serv1, serv2=None):
        await self.send_items("PONG", serv1, serv2)

    async def error(self, message):
        message = f":{message}"
        await self.send_items("ERROR", message)

    # Optional messages bellow

    async def away(self, message=None):
        if message is not None:
            message = f":{message}"
        await self.send_items("AWAY", message)

    async def rehash(self):
        await self.send_items("REHASH")

    async def die(self):
        await self.send_items("DIE")

    async def restart(self):
        await self.send_items("RESTART")

    async def summon(self, user, target=None, channel=None):
        await self.send_items("SUMMON", user, target, channel)

    async def users(self, target=None):
        await self.send_items("USERS", target)

    async def wallops(self, message=None):
        if message is not None:
            message = f":{message}"
        await self.send_items("WALLOPS", message)

    async def userhost(self, nick):
        if isinstance(nick, list):
            if len(nick) > 5:
                raise AttributeError("Userhost command can only get up to 5 users at once")
            nick = " ".join(nick)
        await self.send_items("USERHOST", nick)

    async def ison(self, nick):
        if isinstance(nick, list):
            nick = " ".join(nick)
        await self.send_items("ISON", nick)

    # IRC v3 addons

    async def cap(self, subcom, args):
        if subcom not in _cap_subcommands:
            raise AttributeError
        if isinstance(args, list):
            args = " ".join(args)
        args = f":{args}"
        await self.send_items("CAP", subcom, args)
