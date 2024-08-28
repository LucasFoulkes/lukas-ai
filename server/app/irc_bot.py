# File: irc_bot.py

import os
import shlex
import struct
import irc.client
from jaraco.stream import buffer
import logging
import time
import queue
from dcc_handler import DCCHandler
from message_handler import MessageHandler
from config import Config


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use a more lenient decoding method
irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer


class DCCReceive(irc.client.SimpleIRCClient):
    def __init__(self, message_queue):
        super().__init__()
        self.config = Config()
        self.dcc_handler = DCCHandler(message_queue)
        self.message_handler = MessageHandler(self.config.nickname, message_queue)
        self.is_running = False

    def on_welcome(self, connection, event):
        logger.info("Received welcome message from server")
        connection.join(self.config.channel)
        logger.info(f"Joined {self.config.channel} channel")

    def on_nicknameinuse(self, connection, event):
        self.config.nickname = self.config.nick_generator()
        connection.nick(self.config.nickname)
        self.message_handler.update_nickname(self.config.nickname)
        logger.info(f"Nickname in use, changed to: {self.config.nickname}")

    def on_ctcp(self, connection, event):
        self.dcc_handler.handle_ctcp(self, connection, event)

    def on_dccmsg(self, connection, event):
        self.dcc_handler.handle_dccmsg(self, connection, event)

    def on_disconnect(self, connection, event):
        logger.warning("Disconnected from server")
        self.is_running = False
        self.dcc_handler.prepare_for_new_download()

    def on_all_raw_messages(self, connection, event):
        self.message_handler.process_raw_messages(connection, event)

    def run(self):
        while True:  # Outer loop for reconnection
            try:
                logger.info("Connecting to the server")
                self.connect(self.config.server, self.config.port, self.config.nickname)
            except irc.client.ServerConnectionError as e:
                logger.error(f"Error connecting to server: {e}", exc_info=True)
                logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
                continue

            self.is_running = True
            while self.is_running:
                try:
                    self.reactor.process_once(0.2)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    self.dcc_handler.prepare_for_new_download()  # Reset state on any error

            logger.warning("Disconnected. Attempting to reconnect...")
            time.sleep(60)  # Wait before reconnecting

    def send_message(self, message):
        if self.connection.is_connected():
            self.connection.privmsg(self.config.channel, message)
            logger.info(f"Sent message: {message}")
            return True
        logger.warning("Failed to send message: Not connected")
        return False


if __name__ == "__main__":
    message_queue = queue.Queue()
    dcc_receiver = DCCReceive(message_queue)
    try:
        dcc_receiver.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down.")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
    finally:
        logger.info("Exiting program.")
