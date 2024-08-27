"""
    Event data object, used for events within the module
"""


class Event:

    __slots__ = ("server", "type", "command", "target", "arguments", "prefix", "tags")

    def __init__(self, server, type, command, arguments, prefix=None, tags=None):
        if tags is None:
            tags = {}
        self.server = server
        self.type = type
        self.command = command
        self.target = arguments[0] if arguments else None
        self.arguments = arguments[1:]
        self.prefix = prefix
        self.tags = tags

    def __str__(self):
        result = f"Event(server: {self.server}, type: {self.type}, command: '{self.command}', target: '{self.target}', arguments: {self.arguments}, prefix: '{self.prefix}', tags: {self.tags})"
        return result
