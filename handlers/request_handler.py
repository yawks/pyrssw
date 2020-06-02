import datetime
import logging

from pyparsing import re

from pyrssw_handlers.abstract_pyrssw_request_handler import ENCRYPTED_PREFIX


class RequestHandler():
    """Main instance for every handler."""

    contents: str = ""
    content_type: str = ""
    session_id: str = ""

    def __init__(self):
        self.logger = logging.getLogger()
        self.status: int = 200  # by default

    def _log(self, msg):
        self.logger.info(
            "[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - - " + re.sub(
                "%s[^\\s&]*" % ENCRYPTED_PREFIX, "XXXX", msg))  # anonymize crypted params in logs )

    def get_contents(self) -> str:
        return self.contents

    def set_status(self, status: int):
        self.status = status

    def get_status(self) -> int:
        return self.status

    def get_content_type(self) -> str:
        return self.content_type
