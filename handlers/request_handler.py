import datetime
import logging
import re
from typing import Optional

from pyrssw_handlers.abstract_pyrssw_request_handler import ENCRYPTED_PREFIX


class RequestHandler():
    """Main instance for every handler."""

    contents: str = ""
    content_type: str = ""
    session_id: str = ""

    def __init__(self, source_ip: Optional[str]):
        self.logger = logging.getLogger()
        self.status: int = 200  # by default
        self.source_ip: Optional[str] = source_ip

    def _log(self, msg):
        self.logger.info(
            "[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - %s - %s", self.source_ip, re.sub(
                "%s[^\\s&]*" % ENCRYPTED_PREFIX, "XXXX", msg))  # anonymize crypted params in logs )

    def get_contents(self) -> str:
        return self.contents

    def set_status(self, status: int):
        self.status = status

    def get_status(self) -> int:
        return self.status

    def get_content_type(self) -> str:
        return self.content_type
