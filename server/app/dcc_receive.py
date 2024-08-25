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

        # Use a more lenient buffer to handle decoding issues gracefully
        irc.client.ServerConnection.buffer_class = buffer.LenientDecodingLineBuffer

        self.pattern = re.compile(
            r":\S+ (?:"  # Start with the server name followed by a space
            r"00[1-2]|"  # Numeric codes 001-002
            r"042|"  # Numeric code 042
            r"NOTICE Auth :\*\*\* (?:Looking up your hostname|Could not resolve your hostname|Welcome to ☻irchighway☻)"
            r")"  # End of the pattern group
        )

    async def send_message(self, message: str):
        print(message)  # Print to the console
        await self.websocket.send_text(message)  # Send over WebSocket

    def on_welcome(self, connection, event):
        asyncio.run(
            self.send_message(
                f"Connected to {connection.server} as {connection.nickname}"
            )
        )
        connection.join(self.channel)

    def on_join(self, connection, event):
        if event.target == self.channel and not self.channel_joined:
            self.channel_joined = True
            asyncio.run(self.send_message(f"Joined channel {self.channel}"))

    def on_ctcp(self, connection, event):
        payload = event.arguments[1]
        parts = shlex.split(payload)

        if len(parts) < 5:
            asyncio.run(self.send_message(f"Received invalid CTCP message: {payload}"))
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
            asyncio.run(
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
        asyncio.run(
            self.send_message(
                f"Received file {self.filename} ({self.received_bytes} bytes)."
            )
        )
        self.connection.quit()

    def on_disconnect(self, connection, event):
        sys.exit(0)

    def on_all_raw_messages(self, connection, event):
        message = event.arguments[0]
        if self.pattern.match(message):
            # Split the message by ":" and take the part after the second ":"
            parts = message.split(":", 2)
            if len(parts) > 2:
                output_message = parts[2].strip()
                asyncio.run(self.send_message(output_message))


def start_dcc_receive_client(websocket: WebSocket):
    client = DCCReceive(websocket)
    try:
        client.connect(
            "irc.irchighway.net",
            6667,
            f"lucky_fox_{''.join([str(random.randint(0, 9)) for _ in range(7)])}",
        )
    except irc.client.ServerConnectionError as e:
        print(e)
        sys.exit(1)
    client.start()
