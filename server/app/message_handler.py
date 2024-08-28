import re
import logging

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self, nickname, message_queue):
        self.nickname = nickname
        self.message_queue = message_queue
        self.pattern = re.compile(rf".*\b{self.nickname}\b.*", re.IGNORECASE)

    def update_nickname(self, new_nickname):
        self.nickname = new_nickname
        self.pattern = re.compile(rf".*\b{self.nickname}\b.*", re.IGNORECASE)

    def process_raw_messages(self, connection, event):
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

    def send_to_queue(self, message):
        self.message_queue.put(message)
        logger.info(f"Queued message: {message}")
