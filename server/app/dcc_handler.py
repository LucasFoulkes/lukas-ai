import os
import shlex
import struct
import irc.client
from irc_bot import logger


def handle_ctcp(bot, connection, event):
    try:
        payload = event.arguments[1]
        parts = shlex.split(payload)
        if len(parts) < 2:
            logger.warning(f"Received invalid CTCP message: {payload}")
            return
        command = parts[0]
        if command == "SEND":
            if len(parts) < 5:
                logger.warning(f"Received invalid SEND command: {payload}")
                return
            filename, peer_address, peer_port, size = parts[1:5]
            handle_send_command(
                bot, connection, filename, peer_address, peer_port, size
            )
        else:
            logger.info(f"Received unhandled CTCP command: {command}")
    except Exception as e:
        logger.error(f"Error processing CTCP message: {e}")


def handle_send_command(bot, connection, filename, peer_address, peer_port, size):
    logger.info(f"Received SEND command for file: {filename} ({size} bytes)")
    try:
        bot.filename = os.path.basename(filename)
        if os.path.exists(bot.filename):
            logger.warning(
                f"A file named {bot.filename} already exists. Refusing to save it."
            )
            connection.quit()
            return
        bot.file = open(bot.filename, "wb")
        bot.file_size = int(size)
        bot.received_bytes = 0
        peer_address = irc.client.ip_numstr_to_quad(peer_address)
        peer_port = int(peer_port)
        bot.dcc = bot.dcc_connect(peer_address, peer_port, "raw")
        logger.info(f"Initiated DCC connection for file: {bot.filename}")
    except Exception as e:
        logger.error(f"Error handling SEND command: {e}")


def on_dccmsg(bot, connection, event):
    try:
        data = event.arguments[0]
        bot.file.write(data)
        bot.received_bytes += len(data)
        bot.dcc.send_bytes(struct.pack("!I", bot.received_bytes))
        # Log progress
        progress = (bot.received_bytes / bot.file_size) * 100
        logger.info(f"Download progress: {progress:.2f}%")
    except Exception as e:
        logger.error(f"Error processing DCC message: {e}")


def on_dcc_disconnect(bot, connection, event):
    try:
        bot.file.close()
        logger.info(f"Received file {bot.filename} ({bot.received_bytes} bytes).")
        # Log when the download is complete
        logger.info(f"Download complete: {bot.filename}")
        logger.info(f"File size: {bot.received_bytes} bytes")
        logger.info(f"Saved to: {os.path.abspath(bot.filename)}")
        if bot.received_bytes == bot.file_size:
            logger.info("Download successful: File size matches expected size.")
        else:
            logger.warning(
                f"Warning: Received {bot.received_bytes} bytes, expected {bot.file_size} bytes."
            )
        # connection.quit()
    except Exception as e:
        logger.error(f"Error handling DCC disconnect: {e}")
