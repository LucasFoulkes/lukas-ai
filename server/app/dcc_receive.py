import struct
import re
import irc.client
import shlex
import os
import random
import zipfile
import tempfile
from jaraco.stream import buffer
from fastapi import WebSocket
import asyncio
import json
import logging

logging.basicConfig(level=logging.DEBUG)


class DCCReceive(irc.client.SimpleIRCClient):
    def __init__(self, websocket: WebSocket):
        super().__init__()
        self.websocket = websocket
        self.received_bytes = 0
        self.channel_joined = False
        self.channel = "#ebooks"
        self.filename = None
        self.file = None
        self.running = False
        self.temp_file = None

        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        self.pattern = re.compile(
            r":\S+ (?:" r"NOTICE|" r"00[1-2]|" r"042|" r"SearchBot|" r"lucky_fox" r")"
        )

    def reset_state(self):
        logging.debug("Resetting internal state")
        self.received_bytes = 0
        self.filename = None
        if self.file:
            logging.debug(f"Closing file: {self.file.name}")
            self.file.close()
        self.file = None
        if self.temp_file:
            logging.debug(f"Deleting temp file: {self.temp_file.name}")
            os.unlink(self.temp_file.name)
        self.temp_file = None
        self.running = False

    async def send_message(self, message: str):
        logging.debug(f"Sending message: {message}")
        await self.websocket.send_text(message)

    async def send_json_message(self, data):
        json_message = json.dumps(data)
        logging.debug(f"Sending JSON message: {json_message}")
        await self.websocket.send_text(json_message)

    def send_irc_message(self, message: str):
        logging.debug(f"Sending IRC message: {message}")
        if self.channel_joined:
            self.connection.privmsg(self.channel, message)
            asyncio.create_task(self.send_message(f"Sent to IRC: {message}"))
        else:
            asyncio.create_task(
                self.send_message("Not connected to channel yet. Message not sent.")
            )

    def on_welcome(self, connection, event):
        logging.debug("Received WELCOME from server")
        asyncio.create_task(
            self.send_message(
                f"Connected to {connection.server} as {connection.nickname}"
            )
        )
        connection.join(self.channel)

    def on_join(self, connection, event):
        logging.debug(f"Joined channel: {event.target}")
        if event.target == self.channel and not self.channel_joined:
            self.channel_joined = True
            asyncio.create_task(self.send_message(f"Joined channel {self.channel}"))

    def on_ctcp(self, connection, event):
        payload = event.arguments[1]
        logging.debug(f"Received CTCP: {payload}")
        parts = shlex.split(payload)

        if len(parts) < 5:
            asyncio.create_task(
                self.send_message(f"Received invalid CTCP message: {payload}")
            )
            return

        command, filename, peer_address, peer_port, size = (
            parts[0],
            parts[1],
            parts[2],
            int(parts[3]),
            int(parts[4]),
        )

        if command != "SEND":
            return

        self.filename = os.path.basename(filename)
        logging.debug(f"Preparing to receive file: {self.filename}")

        if not self.filename.endswith(".zip"):
            asyncio.create_task(
                self.send_message(
                    f"Received a non-zip file ({self.filename}). Transfer will be ignored."
                )
            )
            self.connection.quit()
            return

        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        logging.debug(f"Creating temp file: {self.temp_file.name}")
        self.file = open(self.temp_file.name, "wb")

        peer_address = irc.client.ip_numstr_to_quad(peer_address)
        self.dcc = self.dcc_connect(peer_address, peer_port, "raw")

    def on_dccmsg(self, connection, event):
        data = event.arguments[0]
        self.file.write(data)
        self.received_bytes += len(data)
        logging.debug(f"Received {len(data)} bytes, total: {self.received_bytes}")
        self.dcc.send_bytes(struct.pack("!I", self.received_bytes))

    async def unzip_and_send_contents(self):
        logging.debug("Starting to unzip and process the received file")
        if self.temp_file and zipfile.is_zipfile(self.temp_file.name):
            with zipfile.ZipFile(self.temp_file.name, "r") as zip_ref:
                extract_dir = tempfile.mkdtemp()
                zip_ref.extractall(extract_dir)

                all_lines = []
                file_list = os.listdir(extract_dir)
                logging.debug(f"Extracted files: {file_list}")
                for file_name in file_list:
                    file_path = os.path.join(extract_dir, file_name)
                    if os.path.isfile(file_path):
                        with open(file_path, "r") as file:
                            all_lines.extend(file.readlines())

                await self.send_json_message({"list": all_lines})
        logging.debug("Finished processing the zip file")

    def on_dcc_disconnect(self, connection, event):
        logging.debug(f"DCC connection closed for file: {self.filename}")
        if self.file:
            self.file.close()
            asyncio.create_task(
                self.send_message(
                    f"Received file {self.filename} ({self.received_bytes} bytes) and saved to {self.temp_file.name}."
                )
            )
            asyncio.create_task(self.unzip_and_send_contents())
        else:
            asyncio.create_task(
                self.send_message(f"File transfer failed or was cancelled.")
            )
        self.reset_state()

    def on_disconnect(self, connection, event):
        logging.debug("IRC connection closed")
        self.running = False

    def process_and_filter_message(self, message: str):
        logging.debug(f"Processing message: {message}")
        if self.pattern.match(message):
            if "SearchBot" in message or "lucky_fox" in message:
                asyncio.create_task(self.send_message(message))

    def on_privmsg(self, connection, event):
        message = event.arguments[0]
        self.process_and_filter_message(message)

    def on_pubmsg(self, connection, event):
        message = event.arguments[0]
        self.process_and_filter_message(message)

    def on_all_raw_messages(self, connection, event):
        message = event.arguments[0]
        self.process_and_filter_message(message)

    async def start(self):
        logging.debug("Starting DCC client")
        self.running = True
        while self.running:
            self.reactor.process_once(0.2)
            await asyncio.sleep(0.1)


async def start_dcc_receive_client(websocket: WebSocket):
    logging.debug("Initializing DCCReceive client")
    client = DCCReceive(websocket)
    try:
        client.connect(
            "irc.irchighway.net",
            6667,
            f"lucky_fox_{''.join([str(random.randint(0, 9)) for _ in range(7)])}",
        )

        irc_task = asyncio.create_task(client.start())

        while True:
            message = await websocket.receive_text()
            logging.debug(f"Received WebSocket message: {message}")
            if message.startswith("/search "):
                search_message = message[8:]
                client.send_irc_message(search_message)
            elif message == "/quit":
                client.running = False
                client.connection.quit("User requested to quit.")
                break

        await irc_task
    except irc.client.ServerConnectionError as e:
        logging.error(f"Server connection error: {e}")
        await websocket.close()
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
        client.connection.quit("WebSocket disconnected")
        await websocket.close()
    finally:
        client.reset_state()
        logging.debug("Client state has been reset")
