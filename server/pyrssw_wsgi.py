import logging
import os
import sys
from http.cookies import SimpleCookie
from typing import Optional
import random
from config.config import Config
from handlers.bad_request_handler import BadRequestHandler
from handlers.help_handler import HelpHandler
from handlers.launcher_handler import LauncherHandler, SESSION_DURATION
from handlers.request_handler import RequestHandler
from handlers.thumbnails_handler import ThumbnailHandler
from pyrssw_handlers.handlers_manager import HandlersManager
from utils.arguments import parse_command_line


def application(environ, start_response):
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    Config.instance().load_config_file(parse_command_line(sys.argv))

    http: str = "http"
    if "HTTP_X_FORWARDED_PROTO" in environ:
        http = environ["HTTP_X_FORWARDED_PROTO"]
    elif "UWSGI_ROUTER" in environ:
        http = environ["UWSGI_ROUTER"]

    suffix: str = ""
    if "HTTP_X_ORIGINAL_URI" in environ:
        original_uri: str = environ["HTTP_X_ORIGINAL_URI"]
        suffix = original_uri[:len(original_uri)-len(environ["REQUEST_URI"])]

    url_prefix: str = "%s://%s%s" % (http,
                                     environ["HTTP_HOST"],
                                     suffix)

    launcher: WSGILauncherHandler = WSGILauncherHandler(
        environ["REQUEST_URI"], url_prefix)

    cookie: SimpleCookie = SimpleCookie()
    if "HTTP_COOKIE" in environ:
        cookie = SimpleCookie(environ["HTTP_COOKIE"])
    handler: RequestHandler = launcher.get_handler(cookie)

    cookie = SimpleCookie()
    cookie["sessionId"] = handler.session_id
    cookie["sessionId"]["expires"] = SESSION_DURATION
    if len(suffix.split("/")) > 0:
        cookie["sessionId"]["Path"] = suffix.split("/")[0]
    headers = [("Content-type", handler.get_content_type()),
               ("Set-Cookie", cookie["sessionId"].OutputString())]

    start_response(str(handler.get_status()), headers)
    contents = handler.get_contents()
    if isinstance(contents, str):
        return [contents.encode()]
    return [contents]


class WSGILauncherHandler:
    def __init__(self, path: str, serving_url_prefix: Optional[str]):
        self.path: str = path
        self.serving_url_prefix: Optional[str] = serving_url_prefix

    def get_handler(self, cookies: SimpleCookie) -> RequestHandler:
        try:
            module_name = self._parse_module_name()
            handler: Optional[RequestHandler] = None
            suffix_url: str = self.path[len(module_name)+1:]
            if module_name == "":  # root page
                handler = HelpHandler(
                    HandlersManager.instance().get_handlers(), self.serving_url_prefix)
            elif module_name == "thumbnails":
                handler = ThumbnailHandler(suffix_url)
            else:  # use a custom handler via LauncherHandler
                handler = LauncherHandler(module_name, HandlersManager.instance().get_handlers(),
                                          self.serving_url_prefix, suffix_url,
                                          Config.instance().get_crypto_key(),
                                          self._get_sessionid(cookies))
        except Exception as e:
            handler = BadRequestHandler(
                "Error : %s\n%s" % (str(e), self.path))

        return handler

    def _parse_module_name(self):
        module_name = ""
        split_path = self.path.split('/')
        if len(split_path) > 1:
            module_name = split_path[1]
            if module_name.find('?') > -1:
                module_name = module_name.split('?')[0]

        return module_name

    def _get_sessionid(self, cookies: SimpleCookie) -> str:
        """Return the session id from cookie if exists, other generates a random one

        Arguments:
            cookies {SimpleCookie} -- cookies

        Returns:
            str -- a string representing an integer: the sessionId
        """
        sessionid: str = ""

        if "sessionId" in cookies:
            sessionid = cookies["sessionId"].value
        else:
            sessionid = str(random.randrange(100000, 999999999999))

        return sessionid
