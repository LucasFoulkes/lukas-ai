import os
import struct
import logging
import shlex
import irc.client

logger = logging.getLogger(__name__)


class DCCHandler:
    def __init__(self, message_queue):
        self.message_queue = message_queue
        self.received_bytes = 0
        self.file = None
        self.filename = None
        self.expected_file_size = 0
        self.last_progress_report = 0
        self.dcc = None

    def handle_ctcp(self, bot, connection, event):
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

            self.dcc = bot.reactor.dcc("raw")
            self.dcc.connect(peer_address, peer_port)

            # Report initial progress
            self.report_progress()
        except Exception as e:
            logger.error(f"Error in handle_ctcp: {e}", exc_info=True)
            self.prepare_for_new_download()

    def handle_dccmsg(self, bot, connection, event):
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
            logger.error(f"Error in handle_dccmsg: {e}", exc_info=True)
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
                self.dcc.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting DCC: {e}")
        self.dcc = None

    def send_to_queue(self, message):
        self.message_queue.put(message)
        logger.info(f"Queued message: {message}")
