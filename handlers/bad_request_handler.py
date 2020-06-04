from typing import Optional

from handlers.request_handler import RequestHandler


class BadRequestHandler(RequestHandler):
    def __init__(self, path, source_ip: Optional[str]):
        super().__init__(source_ip)
        self.contents = "Unable to fetch resource:" + path
        super()._log(self.contents)
        super().set_status(404)

    def get_content_type(self) -> str:
        return "text/plain"
