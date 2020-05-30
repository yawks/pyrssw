import logging
import re
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from typing import cast
from urllib.parse import unquote_plus

from cryptography.fernet import Fernet

from config.config import Config
from handlers.launcher_handler import ENCRYPTED_PREFIX, SESSION_DURATION
from handlers.request_handler import RequestHandler
from server.abstract_pyrssw_server import AbstractPyRSSWHTTPServer
from server.pyrssw_wsgi import HandlersManager, WSGILauncherHandler


class HTTPRequestHandler(BaseHTTPRequestHandler):
    """Handle every HTTP request.
    Find out which Handler has to be provided to process it.
    Handle http basic auth.
    """

    def do_HEAD(self):
        return

    def do_POST(self):
        # <--- Gets the size of data
        content_length = int(self.headers['Content-Length'])
        # <--- Gets the data itself
        post_data = self.rfile.read(content_length)
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), post_data.decode('utf-8'))
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        HandlersManager.instance().get_handlers()
        fernet = Fernet(Config.instance().get_crypto_key())
        self.wfile.write(("Crypted field: %s" % fernet.encrypt(unquote_plus(
            post_data.decode("utf-8")).split("=")[1].encode("utf-8")).decode("utf-8")).encode("utf-8"))

    def do_GET(self):
        self._process_request()

    def _process_request(self):
        server: AbstractPyRSSWHTTPServer = cast(
            AbstractPyRSSWHTTPServer, self.server)
        if self.check_auth(server.get_auth_key()):

            launcher: WSGILauncherHandler = WSGILauncherHandler(
                self.path, server.get_serving_url_prefix())

            self.respond({'handler': launcher.get_handler(
                SimpleCookie(self.headers.get("Cookie")))})

        else:  # basic auth required
            logging.getLogger().error("Invalid credentials")
            self.send_response(401)
            self.send_header("WWW-Authenticate",
                             "Basic realm=\"PyRSSW Realm\"")
            self.send_header("Content-type", "application/json")
            self.end_headers()

    def check_auth(self, auth_key):
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

    def log_message(self, format, *args):
        params = []
        for arg in args:
            if isinstance(arg, str):
                # anonymize crypted strings in logs
                params.append(re.sub("%s[^\\s&]*" %
                                     ENCRYPTED_PREFIX, "XXXX", arg))
            else:
                params.append(arg)
        logging.getLogger().info(format % tuple(params))

    def handle_http(self, handler: RequestHandler) -> bytes:
        content = None
        status_code = handler.get_status()

        self.send_response(status_code)

        if status_code != 401:
            if status_code == 200:
                content = handler.get_contents()
                self.send_header("Content-type", handler.get_content_type())
                cookie = SimpleCookie()
                cookie["sessionId"] = handler.session_id
                cookie["sessionId"]["expires"] = SESSION_DURATION
                self.send_header(
                    "Set-Cookie", cookie["sessionId"].OutputString())
            elif handler.get_contents() != "":
                content = handler.get_contents()
            else:
                content = "404 Not Found"

        self.end_headers()

        if content is not None:
            if not isinstance(content, bytes):
                content = bytes(content, 'UTF-8')

            return content  # type: ignore
        else:
            return bytes("error no content", 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['handler'])
        self.wfile.write(response)
