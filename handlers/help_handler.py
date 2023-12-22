from typing import Dict, Optional
from typing_extensions import Type
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from handlers.request_handler import RequestHandler


class HelpHandler(RequestHandler):
    """Handles the root page to display the list of loaded handlers
       with their documentation (using docstring)"""

    def __init__(self, handler_types: Dict[str, Type[PyRSSWRequestHandler]], url_prefix: Optional[str], source_ip: Optional[str]):
        super().__init__(source_ip)
        self.handler_types: Dict[str,
                                 Type[PyRSSWRequestHandler]] = handler_types
        self.url_prefix = url_prefix

        content: str = """
<form action="%s" method="post">
    <label for="field">Field to crypt: </label>
    <input type="text" name="field" id="name" required>
</form>
<pre>""" % self.url_prefix
        for _, handler_type in self.handler_types.items():
            module_name = handler_type.__module__.split('.')[1]
            try:
                handler_instance = handler_type()

                content += "<hr/><br/><a style='text-align:center;' href='%s/rss?preview=true&theme=dark'><img style='height:24px;margin-right:5px' src='%s'/>%s</a>\n\n" % (
                    handler_instance.get_handler_name_for_url(),
                    handler_type.get_favicon_url({}),
                    handler_instance.get_handler_name({}))
                if handler_type.__doc__ is not None:
                    content += handler_type.__doc__ + "\n\n"
            except Exception as e:
                content += "<hr/><br/>Error with module : <i>%s</i>\n%s\n\n" %\
                    (module_name, str(e))
        self.contents = content + "</pre>"

    def get_content_type(self) -> str:
        return "text/html"
