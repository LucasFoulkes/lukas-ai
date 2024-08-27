"""
    Basic bot implementation for AIRC. Uses a command handler, only override handlers if necessary.
"""

import asyncio
import inspect
import logging

from .abstracts import Messageable
from .client import DefaultClient
from .errors import HandlerError, CheckFailure
from .events import Event
from .utils import Cooldown


_log = logging.getLogger("airc.bot")


async def empty_handler(*args): pass


def empty_handler_sync(*args): pass


def _split_args(content):
    quotes = False
    escape = False
    args = []
    cur = ""
    for char in content:
        if escape:
            cur += char
            escape = False
        elif char == "\\":
            escape = True
        elif char == "\"":
            quotes = not quotes
            args.append(cur)
            cur = ""
        elif not quotes and char == " ":
            args.append(cur)
            cur = ""
        else:
            cur += char
    if cur is not "":
        args.append(cur)
    return args


class DefaultBot(DefaultClient):

    def __init__(self, prefix, uris=None, *, loop=None):
        super().__init__(uris, loop=loop)

        self.prefix = prefix
        self.all_commands = {}
        self.cogs = {}
        self.events = {}
        self._checks = []
        self.extensions = []

    def add_check(self, predicate):
        if not (asyncio.iscoroutine(predicate) or callable(predicate)):
            raise TypeError("Predicate must be coro or function")
        self._checks.append(predicate)

    def remove_check(self, predicate):
        try:
            self._checks.remove(predicate)
        except ValueError:
            pass

    def add_command(self, command):
        if not isinstance(command, Command):
            raise TypeError("Passed command must subclass Command")

        if command.name in self.all_commands:
            raise ValueError("Command already exists")

        self.all_commands[command.name] = command
        _log.debug(f"Added command {command.name}")
        for alias in command.aliases:
            if alias in self.all_commands:
                raise ValueError("Command alias already exists")
            self.all_commands[alias] = command

    def remove_command(self, name):
        command = self.all_commands.pop(name, None)
        if command is None:
            return

        if name in command.aliases:
            return command

        for alias in command.aliases:
            self.all_commands.pop(alias)
        return command

    def command(self, *args, **kwargs):
        def decorator(func):
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result
        return decorator

    def add_cog(self, cog):
        self.cogs[type(cog).__name__] = cog

        try:
            check = getattr(cog, f"_{cog.__class__.__name__}__global_check")
        except AttributeError:
            pass
        else:
            self.add_check(check)

        members = inspect.getmembers(cog)
        for name, member in members:
            if isinstance(member, Command):
                self.add_command(member)
                continue

            if name.startswith("on_"):
                event_name = name[3:]
                if self.events.get(event_name) is None:
                    self.events[event_name] = []
                self.events[event_name].append(member)

    def remove_cog(self, name):
        cog = self.cogs.pop(name, None)
        if cog is None:
            return

        members = inspect.getmembers(cog)
        for name, member in members:
            if isinstance(member, Command):
                self.remove_command(member.name)
                continue

            if name.startswith("on_"):
                event_name = name[3:]
                self.events[event_name].remove(member)

        try:
            check = getattr(cog, f"_{cog.__class__.__name__}__global_check")
        except AttributeError:
            pass
        else:
            self.remove_check(check)

        unloader_name = f"_{cog.__class__.__name__}__unload"
        try:
            unloader = getattr(cog, unloader_name)
        except AttributeError:
            pass
        else:
            unloader()

        del cog

    def load_extension(self, name):
        import importlib
        try:
            module = importlib.import_module(name)
            module.setup(self)
            self.extensions.append(module)
        except Exception as e:
            print(e)

    def unload_extension(self, ext):
        try:
            self.extensions.remove(ext)
            ext.teardown()
        except Exception as e:
            print(e)

    async def get_prefix(self, message):
        prefix = ret = self.prefix
        if callable(prefix):
            ret = prefix(self, message)
            if asyncio.iscoroutine(ret):
                ret = await ret
        if isinstance(prefix, (list, tuple)):
            ret = [_ for _ in prefix if _]

        if not ret:
            raise AssertionError("Invalid Prefix, may be empty string, list, or None.")

        return ret

    async def _dispatch(self, event):
        if event.type.startswith("command"):
            handler = getattr(self, "handle_" + event.type, empty_handler_sync)
            try:
                handler(event.target, *event.arguments)
            except Exception as e:
                raise HandlerError(e)
            handler = getattr(self, "on_" + event.type, empty_handler)
            try:
                await handler(event.target, *event.arguments)
                for event in self.events[event.type]:
                    await event(event.target, *event.arguments)
            except Exception as e:
                raise HandlerError(e)
        else:
            await super()._dispatch(event)

    async def _handle_command(self, event):
        ctx = await self.build_context(event)
        if ctx.command is not None:
            await self.invoke_command(ctx)

    async def build_context(self, event):
        channel = self.get_channel(event.target)
        user = channel.get_user(event.prefix.nick)
        message = TwitchMessage(event, channel, user)
        ctx = Context(self, message)

        prefix = await self.get_prefix(message)
        if isinstance(prefix, (list, tuple)):
            for pref in prefix:
                if message.content.startswith(pref):
                    ctx.invoked_prefix = pref
                    break
        elif message.content.startswith(prefix):
                ctx.invoked_prefix = prefix

        if ctx.invoked_prefix:
            raw_list = _split_args(message.content)
            ctx.invoker = raw_list[0][len(ctx.invoked_prefix):]
            ctx.args = raw_list[1:]

        ctx.command = self.all_commands.get(ctx.invoker)

        return ctx

    async def invoke_command(self, ctx):
        try:
            if not await self.can_run(ctx):
                raise CheckFailure("Global check failed")
            await self._dispatch(Event(self.server, "command", [ctx]))
            await ctx.command.invoke(ctx)
        except Exception as e:
            error_event = Event(self.server, "commanderror", [ctx, e])
            await self._dispatch(error_event)

    async def can_run(self, ctx):

        for check in self._checks:
            result = check(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                return False

        return True

    async def on_privmsg(self, event):
        await self._handle_command(event)


class TwitchMessage:

    __slots__ = ("id", "content", "bits", "emotes", "emote_only", "timestamp", "channel", "author")

    def __init__(self, event, channel, author):
        tags = event.tags
        self.id = tags.get("id", "")
        self.content = event.arguments[0]
        self.bits = int(tags.get("bits", 0))
        self.emotes = tags.get("emotes")
        self.emote_only = bool(int(tags.get("emote-only", False)))
        self.timestamp = int(tags.get("tmi-sent-ts", -1))

        self.channel = channel
        self.author = author


class Context(Messageable):

    __slots__ = ("bot", "message", "invoked_prefix", "args", "invoker", "command")

    def __init__(self, bot, message):
        self.bot = bot
        self.message = message

        self.invoked_prefix = None
        self.args = []
        self.invoker = None

        self.command = None

    @property
    def channel(self):
        return self.message.channel

    @property
    def author(self):
        return self.message.author

    @property
    def me(self):
        return self.channel.me

    @property
    def server(self):
        return self.bot.server

    async def send(self, message):
        await self.channel.send(message)


class Command:  # TODO: add command groups

    __slots__ = ("name", "callback", "active", "hidden", "aliases", "help", "params", "checks", "cooldowns")

    def __init__(self, name, callback, **options):
        if not isinstance(name, str):
            raise TypeError('Name of a command must be a string.')
        self.name = name
        self.callback = callback

        self.checks = options.get("checks", [])
        self.cooldowns = options.get("cooldowns", [])
        self.active = options.get("active", True)
        self.hidden = options.get("hidden", False)
        self.aliases = options.get("aliases", [])
        self.help = options.get("help")
        signature = inspect.signature(callback)
        self.params = signature.parameters.copy()

    def _parse_arguments(self, ctx):
        # Quick notes: one arg per variable, except for positional only or keyword only.
        # Error if missing when required, keyword only it will fill with empty string.
        args = []
        kwargs = {}
        i = 0
        for param in self.params:
            if param == "ctx":
                continue
            fparam = self.params[param]
            if fparam.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
                try:
                    args.append(ctx.args[i])  # TODO: annotation cast
                    i += 1
                except IndexError:
                    if fparam.default == fparam.empty:
                        raise  # TODO: module errors
                    args.append(fparam.default)
            if fparam.kind is inspect.Parameter.VAR_POSITIONAL:
                for arg in ctx.args[i:]:
                    args.append(arg)
                break
            if fparam.kind is inspect.Parameter.KEYWORD_ONLY:
                kwargs[param] = ' '.join(ctx.args[i:])
                break
        return args, kwargs

    async def invoke(self, ctx):
        if not await self.can_run(ctx):
            raise CheckFailure("Command check failed")
        try:
            args, kwargs = self._parse_arguments(ctx)
            await self.callback(ctx, *args, **kwargs)
        except Exception as e:
            _log.warning(e)

    async def can_run(self, ctx):

        if not self.active:
            return self.active

        for check in self.checks:
            result = check(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            if not result:
                return False

        mark = True
        for cooldown in self.cooldowns:
            name = cooldown.name
            result = 0
            if name == "":
                result = cooldown.can_run()
            elif name[0] == "#" and ctx.channel.name == name:
                result = cooldown.can_run()
            elif name == ctx.author.name:
                result = cooldown.can_run()
            if result:
                mark = False
        return mark


def command(name=None, cls=Command, **attrs):

    def decorator(func):
        if isinstance(func, Command):
            raise TypeError("Function is already a Command")

        try:
            checks = func.__command_checks__
            checks.reverse()
            del func.__command_checks__
        except AttributeError:
            checks = []

        try:
            cooldowns = func.__cooldowns__
            cooldowns.reverse()
            del func.__cooldowns__
        except AttributeError:
            cooldowns = []

        help_doc = attrs.get('help')
        if help_doc is not None:
            help_doc = inspect.cleandoc(help_doc)
        else:
            help_doc = inspect.getdoc(func)
            if isinstance(help_doc, bytes):
                help_doc = help_doc.decode('utf-8')

        attrs['help'] = help_doc

        cname = name or func.__name__
        return cls(name=cname, callback=func, checks=checks, cooldowns=cooldowns, **attrs)

    return decorator


def check(predicate):

    def decorator(func):
        if isinstance(func, Command):
            func.checks.append(predicate)
        else:
            if not hasattr(func, "__command_checks__"):
                func.__command_checks__ = []
            func.__command_checks__.append(predicate)

        return func
    return decorator


def broadcaster_only():
    return check(lambda x: x.author.broadcaster)


def mod_only():
    return check(lambda x: x.author.mod)


def subscriber_only():
    return check(lambda x: x.author.subscriber)


def cooldown(per, time, target=""):

    def decorator(func):
        if isinstance(func, Command):
            func.cooldowns.append(Cooldown(per, time, target))
        else:
            if not hasattr(func, "__cooldowns__"):
                func.__cooldowns__ = []
            func.__cooldowns__.append(Cooldown(per, time, target))

        return func
    return decorator
