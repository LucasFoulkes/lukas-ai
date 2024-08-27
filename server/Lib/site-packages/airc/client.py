"""
    Master class for the AIRC
"""

import asyncio
import logging

from . import server
from .abstracts import Messageable


__all__ = ("User", "Channel", "DefaultClient")


log = logging.getLogger("airc.client")


async def empty_handler(event): pass


def empty_handler_sync(event): pass


class User(Messageable):

    def __init__(self, server, name):
        self.server = server
        self.name = name

    def message(self, message):
        self.server.privmsg(self.name, message)


class Channel(Messageable):

    def __init__(self, server, name):
        self.server = server
        self.name = name

    def message(self, message):
        self.server.privmsg(self.name, message)


class DefaultClient:

    __slots__ = ("loop", "server_type", "connections", "handlers")

    def __init__(self, uris=None, *, server_type=server.DefaultServer, loop=None):

        self.loop = loop or asyncio.get_event_loop()
        self.server_type = server_type

        self.connections = []
        self.handlers = {}

        # self.add_handler("ping", _ponger)

        if not isinstance(uris, (list, tuple)):
            uris = (uris,)
        for uri in uris:
            self.server(uri)

    def server(self, uri):
        server = self.server_type(uri, self, loop=self.loop)
        self.connections.append(server)
        return server

    def run(self, *args, **kwargs):
        task = self.loop.create_task(self.start(*args, **kwargs))
        if not self.loop.is_running():
            self.loop.run_until_complete(task)

    async def start(self, *args, **kwargs):
        tasks = []
        names = kwargs.get("names", [])
        passwds = kwargs.get("passwds", [])
        for server in self.connections:
            if not server.connected:
                # TODO: handle failed connection?
                await server.connect(names.pop(0), password=passwds.pop(0))
            tasks.append(self.loop.create_task(server.process_data()))
        while len(tasks) > 0:
            for task in tasks:
                if task.done():
                    tasks.remove(task)
                    server = await task
                    tasks.append(self.loop.create_task(server.process_data()))
                elif task.cancelled():
                    tasks.remove(task)
            await asyncio.sleep(1)

    async def _handle_event(self, event):
        all_handler = getattr(self, "on_all_events", None)
        if all_handler is not None:
            await all_handler(event)
        event_handler = getattr(self, "on_" + event.command, None)
        if event_handler is not None:
            await event_handler(event)

    async def on_ping(self, event):
        await event.server.pong(event.target)
