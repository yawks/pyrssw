import logging
from http.server import BaseHTTPRequestHandler
from typing import Optional, cast
from zipfile import error

from handlers.bad_request_handler import BadRequestHandler
from handlers.help_handler import HelpHandler
from handlers.launcher_handler import LauncherHandler
from handlers.request_handler import RequestHandler
from handlers.thumbnails_handler import ThumbnailHandler
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from server.abstract_pyrssw_server import AbstractPyRSSWHTTPServer


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Handle every HTTP request.
    Find out which Handler has to be provided to process it.
    Handle http basic auth.
    """

    def do_HEAD(self):
        return

    def do_GET(self):
        server: AbstractPyRSSWHTTPServer = cast(
            AbstractPyRSSWHTTPServer, self.server)
        if self.check_auth(self.headers, server.get_auth_key()):
            try:
                module_name = self._parse_module_name()
                handler: Optional[RequestHandler] = None
                suffix_url: str = self.path[len(module_name)+1:]

                if module_name == "":  # root page
                    handler = HelpHandler(
                        server.get_handlers(), server.get_serving_url_prefix())
                elif module_name == "thumbnails":
                    handler = ThumbnailHandler(suffix_url)
                else:  # use a custom handler via LauncherHandler
                    handler = LauncherHandler(module_name, server.get_handlers(),
                                              server.get_serving_url_prefix(), suffix_url,
                                              server.get_crypto_key())
            except Exception as e:
                handler = BadRequestHandler(
                    "Error : %s\n%s" % (str(e), self.path))

            self.respond({'handler': handler})

        else:  # basic auth required
            logging.getLogger().error("Invalid credentials")
            self.send_response(401)
            self.send_header("WWW-Authenticate",
                             "Basic realm=\"PyRSSW Realm\"")
            self.send_header("Content-type", "application/json")
            self.end_headers()

    def check_auth(self, headers, auth_key):
        """ Process basic auth authentication check """
        auth_ok = False
        if auth_key is None:
            # if no authorization key is defined, auth is always True
            auth_ok = True
        elif self.headers.get("Authorization") == 'Basic ' + str(auth_key):
            auth_ok = True
        elif not self.headers.get("Authorization") is None:
            logging.getLogger().error("Invalid credentials")

        return auth_ok

    def _parse_module_name(self):
        module_name = ""
        split_path = self.path.split('/')
        if len(split_path) > 1:
            module_name = split_path[1]
            if module_name.find('?') > -1:
                module_name = module_name.split('?')[0]

        return module_name

    def handle_http(self, handler: RequestHandler) -> bytes:
        content = None
        status_code = handler.get_status()

        self.send_response(status_code)

        if status_code != 401:
            if status_code == 200:
                content = handler.get_contents()
                self.send_header('Content-type', handler.get_content_type())
            elif handler.get_contents() != "":
                content = handler.get_contents()
            else:
                content = "404 Not Found"

        self.end_headers()

        if not content is None:
            if isinstance(content, bytes):
                return content  # type: ignore
            else:
                return bytes(content, 'UTF-8')
        else:
            return bytes("error no content", 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['handler'])
        self.wfile.write(response)
