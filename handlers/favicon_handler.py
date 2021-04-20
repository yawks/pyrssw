from glob import glob
import importlib
import os

import requests
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from typing import List, Optional, Type
from urllib.parse import urlparse
from handlers.request_handler import RequestHandler


class FaviconHandler(RequestHandler):
    """Favicon provider.
    """

    def __init__(self, handler_types: List[Type[PyRSSWRequestHandler]], referer: str, source_ip: Optional[str]):
        super().__init__(source_ip)
        parsed = urlparse(referer)

        # returns an empty image
        self.contents = "R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        self.handler_types: List[Type[PyRSSWRequestHandler]] = handler_types

        for handler_type in self.handler_types:
            module_name = handler_type.__module__.split('.')[1]
            try:
                # try to intanciate the class to display error if any
                handler_type()
                if handler_type.get_handler_name() in parsed.path:
                    self.contents = requests.get(
                        handler_type.get_favicon_url()).content
                    break

            except Exception as e:
                self._log("<hr/><br/>Error with module : <i>%s</i>\n%s\n\n" %
                          (module_name, str(e)))

        self.content_type = "image/webp"
