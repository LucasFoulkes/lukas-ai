import os
import shlex
import struct
import irc.client
from nick_generator import nick_generator
import queue
import re
from jaraco.stream import buffer
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use a more lenient decoding method
irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer


class DCCReceive(irc.client.SimpleIRCClient):
    def __init__(self, message_queue):
        super().__init__()
        self.received_bytes = 0
        self.nickname = nick_generator()
        self.message_queue = message_queue
        self.is_running = False
        self.pattern = re.compile(rf".*\b{self.nickname}\b.*", re.IGNORECASE)
        self.dcc = None
        self.file = None
        self.filename = None
        self.expected_file_size = 0
        self.last_progress_report = 0
        logger.info(f"Initialized DCCReceive with nickname: {self.nickname}")

    def send_to_queue(self, message):
        self.message_queue.put(message)
        logger.info(f"Queued message: {message}")

    def on_nicknameinuse(self, connection, event):
        self.nickname = nick_generator()
        connection.nick(self.nickname)
        self.pattern = re.compile(rf".*\b{self.nickname}\b.*", re.IGNORECASE)
        logger.info(f"Nickname in use, changed to: {self.nickname}")

    def on_welcome(self, connection, event):
        logger.info("Received welcome message from server")
        connection.join("#ebooks")
        logger.info("Joined #ebooks channel")

    def on_ctcp(self, connection, event):
        logger.debug(f"Received CTCP event: {event}")
        try:
            ctcp_type = event.arguments[0]
            if ctcp_type != "DCC":
                logger.info(f"Ignoring non-DCC CTCP: {ctcp_type}")
                return

            payload = event.arguments[1]
            parts = shlex.split(payload)

            if len(parts) < 5:
                logger.warning(f"Received DCC command with insufficient parts: {parts}")
                return

            command, filename, peer_address, peer_port, size = parts[:5]

            if command != "SEND":
                logger.info(f"Ignoring non-SEND DCC command: {command}")
                return

            self.prepare_for_new_download()

            self.filename = os.path.basename(filename)
            self.file = open(self.filename, "wb")
            self.expected_file_size = int(size)
            peer_address = irc.client.ip_numstr_to_quad(peer_address)
            peer_port = int(peer_port)
            logger.info(
                f"Initiating DCC connection to {peer_address}:{peer_port} for file {self.filename}"
            )

            self.dcc = self.reactor.dcc("raw")
            self.dcc.connect(peer_address, peer_port)

            # Report initial progress
            self.report_progress()
        except Exception as e:
            logger.error(f"Error in on_ctcp: {e}", exc_info=True)
            self.prepare_for_new_download()

    def on_dccmsg(self, connection, event):
        try:
            data = event.arguments[0]
            if self.file:
                self.file.write(data)
                self.received_bytes += len(data)
                self.dcc.send_bytes(struct.pack("!I", self.received_bytes))
                logger.debug(
                    f"Received {len(data)} bytes, total: {self.received_bytes}"
                )

                self.report_progress()

                if self.received_bytes >= self.expected_file_size:
                    self.finalize_download()
            else:
                logger.error("Received DCC message but file is not open.")
        except Exception as e:
            logger.error(f"Error in on_dccmsg: {e}", exc_info=True)
            self.prepare_for_new_download()

    def report_progress(self):
        if self.expected_file_size > 0:
            progress = (self.received_bytes / self.expected_file_size) * 100
            current_progress = int(progress)

            # Report progress at every 5% increment
            if (
                current_progress % 5 == 0
                and current_progress != self.last_progress_report
            ):
                self.last_progress_report = current_progress
                progress_message = (
                    f"Download progress for {self.filename}: {current_progress}%"
                )
                self.send_to_queue(progress_message)

    def on_dcc_disconnect(self, connection, event):
        self.finalize_download()

    def finalize_download(self):
        if self.file:
            self.file.close()
            completion_message = (
                f"Download completed: {self.filename} ({self.received_bytes} bytes)"
            )
            self.send_to_queue(completion_message)
        self.prepare_for_new_download()

    def prepare_for_new_download(self):
        if self.file:
            self.file.close()
        self.file = None
        self.filename = None
        self.received_bytes = 0
        self.expected_file_size = 0
        self.last_progress_report = 0
        if self.dcc:
            try:
                # Attempt to close the socket directly
                if hasattr(self.dcc, "socket") and self.dcc.socket:
                    self.dcc.socket.close()
                # Remove the DCC connection from the reactor's list if it exists
                if hasattr(self.reactor, "connections"):
                    self.reactor.connections = [
                        conn
                        for conn in self.reactor.connections
                        if conn is not self.dcc
                    ]
            except Exception as e:
                logger.error(f"Error during DCC cleanup: {e}", exc_info=True)
            finally:
                self.dcc = None
        logger.info("Prepared for new download")

    def on_disconnect(self, connection, event):
        logger.warning("Disconnected from server")
        self.is_running = False
        self.prepare_for_new_download()

    def on_all_raw_messages(self, connection, event):
        for arg in event.arguments:
            try:
                decoded_arg = (
                    arg.decode("utf-8", errors="replace")
                    if isinstance(arg, bytes)
                    else arg
                )
                if self.pattern.match(decoded_arg):
                    self.send_to_queue(decoded_arg)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)

    def run(self):
        while True:  # Outer loop for reconnection
            try:
                logger.info("Connecting to the server")
                self.connect("irc.irchighway.net", 6667, self.nickname)
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
                    self.prepare_for_new_download()  # Reset state on any error

            logger.warning("Disconnected. Attempting to reconnect...")
            time.sleep(60)  # Wait before reconnecting

    def send_message(self, message):
        if self.connection.is_connected():
            self.connection.privmsg("#ebooks", message)
            logger.info(f"Sent message: {message}")
            return True
        logger.warning("Failed to send message: Not connected")
        return False
