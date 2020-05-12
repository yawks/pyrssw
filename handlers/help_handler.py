import traceback
from typing import List, Optional

from typing_extensions import Type

from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from handlers.request_handler import RequestHandler


class HelpHandler(RequestHandler):
    """Handles the root page to display the list of loaded handlers with their documentation (using docstring)"""

    def __init__(self, handler_types: List[Type[PyRSSWRequestHandler]], url_prefix: Optional[str]):
        super().__init__()
        self.handler_types: List[Type[PyRSSWRequestHandler]] = handler_types
        self.url_prefix = url_prefix

        content: str = "<pre>"
        for handler_type in self.handler_types:
            module_name = handler_type.__module__.split('.')[1]
            try:
                handler_type()  # try to intanciate the class to display error if any
                content += "<hr/><br/><a href='/%s/rss'>%s</a>\n\n" % (
                    handler_type.get_handler_name(), handler_type.get_handler_name())
                if not handler_type.__doc__ is None:
                    content += handler_type.__doc__ + "\n\n"
            except Exception as e:
                content += "<hr/><br/>Error with module : <i>%s</i>\n%s\n\n" % (
                    module_name, str(e))
        self.contents = content + "</pre>"
    
    def get_content_type(self) -> str:
        return "text/html"
