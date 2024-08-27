import irc.bot
import irc.strings
import os
import struct
import logging
import re
import shlex

logging.basicConfig(level=logging.DEBUG)


class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, sio=None, sid=None):
        super().__init__([(server, port)], nickname, nickname)
        self.channel = channel
        self.sio = sio
        self.sid = sid  # Pass the sid from the WebSocket connection
        self.reset_transfer_state()

    def reset_transfer_state(self):
        """Resets the state variables used for DCC file transfers."""
        self.file = None
        self.filename = None
        self.total_bytes = 0
        self.received_bytes = 0
        self.dcc_connection = None
        logging.debug("Transfer state reset.")

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        m = e.arguments[0]

    def on_pubmsg(self, c, e):
        m = e.arguments[0]

    def on_all_raw_messages(self, c, e):
        m = e.arguments[0]
        pattern = re.compile(
            r":\S+ (?:(?:NOTICE)|(?:00[1-2])|(?:042)|(?:<<SearchBot>>)|(?:lucky_fox))"
        )
        if pattern.search(m):
            if self.sio and self.sid:
                self.sio.emit("response", {"message": m}, room=self.sid)

    def on_ctcp(self, connection, event):
        try:
            if event.type != "ctcp":
                return

            if len(event.arguments) < 2:
                logging.error("CTCP message has insufficient arguments.")
                return

            # Attempt to decode the message safely
            try:
                payload = event.arguments[1].encode("latin-1").decode("utf-8")
            except UnicodeDecodeError:
                logging.warning(
                    "Failed to decode CTCP message using UTF-8; trying latin-1."
                )
                payload = event.arguments[1]  # Use the raw message if decoding fails

            parts = shlex.split(payload)
            if len(parts) < 5:
                logging.error(f"Unexpected CTCP message format: {parts}")
                return

            command = parts[0]
            if command != "SEND":
                logging.debug(f"CTCP command not supported: {command}")
                return

            self.filename = os.path.basename(parts[1].strip('"'))
            peer_address = parts[-3]
            peer_port = int(parts[-2])
            self.total_bytes = int(parts[-1])

            if os.path.exists(self.filename):
                logging.error(
                    f"File {self.filename} already exists. Refusing to overwrite."
                )
                return

            self.file = open(self.filename, "wb")
            self.dcc_connection = self.dcc_connect(
                irc.client.ip_numstr_to_quad(peer_address), peer_port, "raw"
            )
            logging.info(
                f"Started file transfer: {self.filename}, Size: {self.total_bytes} bytes."
            )

        except Exception as e:
            logging.error(f"Error in on_ctcp: {e}")
            self.cleanup_dcc_transfer()

    def on_dccmsg(self, connection, event):
        try:
            if connection != self.dcc_connection:
                logging.error("Received DCC message from an unexpected connection.")
                return

            data = event.arguments[0]
            self.received_bytes += len(data)

            if self.received_bytes > self.total_bytes:
                excess_bytes = self.received_bytes - self.total_bytes
                self.file.write(data[:-excess_bytes])
                logging.warning(
                    f"Received more bytes than expected for {self.filename}, truncating."
                )
            else:
                self.file.write(data)

            percentage = (self.received_bytes / self.total_bytes) * 100
            logging.info(f"Download progress for {self.filename}: {percentage:.2f}%")

            if self.sio and self.sid:
                self.sio.emit(
                    "download_progress",
                    {"filename": self.filename, "percentage": percentage},
                    room=self.sid,
                )

            if self.received_bytes >= self.total_bytes:
                logging.info(f"Download complete for {self.filename}.")
                self.cleanup_dcc_transfer()

        except Exception as e:
            logging.error(f"Error in on_dccmsg: {e}")
            self.cleanup_dcc_transfer()

    def cleanup_dcc_transfer(self):
        try:
            if self.file:
                self.file.close()
                logging.info(f"File {self.filename} closed.")
            if self.dcc_connection and hasattr(self.dcc_connection, "disconnect"):
                self.dcc_connection.disconnect()
                logging.info(f"DCC connection for {self.filename} closed.")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        finally:
            self.reset_transfer_state()

    def _decode_message(self, message):
        if isinstance(message, bytes):
            try:
                return message.decode("utf-8")
            except UnicodeDecodeError:
                return message.decode("latin-1")
        return message  # If it's already a string, just return it

    def disconnect(self):
        super().disconnect()

    def die(self, reason=""):
        self.disconnect()
