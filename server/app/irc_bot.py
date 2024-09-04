import irc.bot
import asyncio
import logging
from jaraco.stream import buffer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LenientDecodingLineBuffer(buffer.DecodingLineBuffer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.errors = "replace"

    def decode(self, buf):
        try:
            return buf.decode("utf-8", errors=self.errors)
        except UnicodeDecodeError:
            return buf.decode("latin-1", errors=self.errors)


class IRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port, sio, queue):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.sio = sio
        self.queue = queue
        self.connection.buffer_class = LenientDecodingLineBuffer
        self.received_bytes = 0

    def on_welcome(self, connection, event):
        connection.join(self.channel)
        logger.info(f"Joined channel: {self.channel}")

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        asyncio.run(self.sio.emit("response", {"message": message}))
        logger.info(f"Emitted message: {message}")

    def on_prvmsg(self, connection, event):
        message = event.arguments[0]
        asyncio.run(self.sio.emit("response", {"message": message}))
        logger.info(f"Emitted message: {message}")

    def send_message(self, message):
        if self.connection.is_connected():
            self.connection.privmsg(self.channel, message)
            logger.info(f"Sent message: {message}")
            return True
        logger.warning("Failed to send message: Not connected")
        return False

    # def on_ctcp(self, connection, event):
    #     from dcc_handler import handle_ctcp

    #     handle_ctcp(self, connection, event)

    # def on_dccmsg(self, connection, event):
    #     from dcc_handler import on_dccmsg

    #     on_dccmsg(self, connection, event)

    # def on_dcc_disconnect(self, connection, event):
    #     from dcc_handler import on_dcc_disconnect

    #     on_dcc_disconnect(self, connection, event)
