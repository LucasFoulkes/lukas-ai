import struct
import sys
import re
import irc.client
import shlex
import os
import random
from jaraco.stream import buffer
from fastapi import WebSocket
import asyncio


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

        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        self.pattern = re.compile(
            r":\S+ (?:"
            r"00[1-2]|"
            r"042|"
            r"NOTICE Auth :\*\*\* (?:Looking up your hostname|Could not resolve your hostname|Welcome to ☻irchighway☻)|"
            r"SearchBot"
            r")"
        )

    async def send_message(self, message: str):
        print(message)
        await self.websocket.send_text(message)

    def send_irc_message(self, message: str):
        if self.channel_joined:
            self.connection.privmsg(self.channel, message)
            asyncio.create_task(self.send_message(f"Sent to IRC: {message}"))
        else:
            asyncio.create_task(
                self.send_message("Not connected to channel yet. Message not sent.")
            )

    def on_welcome(self, connection, event):
        asyncio.create_task(
            self.send_message(
                f"Connected to {connection.server} as {connection.nickname}"
            )
        )
        connection.join(self.channel)

    def on_join(self, connection, event):
        if event.target == self.channel and not self.channel_joined:
            self.channel_joined = True
            asyncio.create_task(self.send_message(f"Joined channel {self.channel}"))

    def on_ctcp(self, connection, event):
        payload = event.arguments[1]
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
        if os.path.exists(self.filename):
            asyncio.create_task(
                self.send_message(
                    f"A file named {self.filename} already exists. Refusing to save it."
                )
            )
            self.connection.quit()
            return

        self.file = open(self.filename, "wb")
        peer_address = irc.client.ip_numstr_to_quad(peer_address)
        self.dcc = self.dcc_connect(peer_address, peer_port, "raw")

    def on_dccmsg(self, connection, event):
        data = event.arguments[0]
        self.file.write(data)
        self.received_bytes += len(data)
        self.dcc.send_bytes(struct.pack("!I", self.received_bytes))

    def on_dcc_disconnect(self, connection, event):
        self.file.close()
        asyncio.create_task(
            self.send_message(
                f"Received file {self.filename} ({self.received_bytes} bytes)."
            )
        )
        self.connection.quit()

    def on_disconnect(self, connection, event):
        self.running = False

    def on_all_raw_messages(self, connection, event):
        message = event.arguments[0]
        if self.pattern.match(message):
            parts = message.split(":", 2)
            if len(parts) > 2:
                output_message = parts[2].strip()
                asyncio.create_task(self.send_message(output_message))

    async def start(self):
        self.running = True
        while self.running:
            self.reactor.process_once(0.2)
            await asyncio.sleep(0.1)


async def start_dcc_receive_client(websocket: WebSocket):
    client = DCCReceive(websocket)
    try:
        client.connect(
            "irc.irchighway.net",
            6667,
            f"lucky_fox_{''.join([str(random.randint(0, 9)) for _ in range(7)])}",
        )

        # Start the IRC client in a separate task
        irc_task = asyncio.create_task(client.start())

        # Handle WebSocket messages
        while True:
            message = await websocket.receive_text()
            if message.startswith("/search "):
                search_message = message[8:]  # Remove "/search " prefix
                client.send_irc_message(search_message)
            elif message == "/quit":
                client.running = False
                break

        # Wait for the IRC client to finish
        await irc_task
    except irc.client.ServerConnectionError as e:
        print(e)
        await websocket.close()
    except Exception as e:
        print(f"Error: {e}")
        client.connection.quit("WebSocket disconnected")
        await websocket.close()
