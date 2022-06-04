import requests
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from typing import Dict, Optional, Type
from urllib.parse import urlparse
from handlers.request_handler import RequestHandler


class FaviconHandler(RequestHandler):
    """Favicon provider.
    """

    def __init__(self, handler_types: Dict[str, Type[PyRSSWRequestHandler]], referer: str, source_ip: Optional[str]):
        super().__init__(source_ip)
        parsed = urlparse(referer)

        # returns an empty image
        self.contents = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        self.handler_types: Dict[str, Type[PyRSSWRequestHandler]] = handler_types

        for handler_name, handler_type in self.handler_types.items():
            try:
                #handler_instance = handler_type()
                if handler_name in parsed.path:
                    self.contents = str(requests.get(
                        handler_type.get_favicon_url({})).content)
                    break

            except Exception as e:
                self._log("<hr/><br/>Error with module : <i>%s</i>\n%s\n\n" %
                          (handler_name, str(e)))

        self.content_type = "image/webp"
