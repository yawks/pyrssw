import datetime
import logging


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
            "[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - - " + msg)

    def get_contents(self) -> str:
        return self.contents

    def set_status(self, status: int):
        self.status = status

    def get_status(self) -> int:
        return self.status

    def get_content_type(self) -> str:
        return self.content_type
