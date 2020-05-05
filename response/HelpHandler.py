from response.RequestHandler import RequestHandler
from typing import List

class HelpHandler(RequestHandler):
    """Handles the root page to display the list of loaded handlers with their documentation (using docstring)"""

    def __init__(self, handlers: List[RequestHandler]):
        super().__init__("", "help", "")
        self.handlers = handlers

    def get_content(self, url:str, parameters: dict) -> str:
        content = "<pre>"
        for handler in self.handlers:
            content += "<hr/><br/><a href='%srss'>%s</a>\n\n" % (handler.url_prefix, handler.__module__.split('.')[1])
            if not handler.__doc__ is None:
                content += handler.__doc__ + "\n\n"
        return content + "</pre>"