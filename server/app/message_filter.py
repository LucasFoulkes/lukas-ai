import re


class MessageFilter:
    def __init__(self):
        self.pattern = re.compile(
            r":\S+ (?:" r"NOTICE|" r"00[1-2]|" r"042|" r"SearchBot|" r"lucky_fox" r")"
        )

    def filter_message(self, message: str) -> bool:
        """
        Returns True if the message matches the pattern and should be processed, False otherwise.
        """
        return bool(self.pattern.match(message))
