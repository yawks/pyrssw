import os
import importlib

import ssl
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from response.BadRequestHandler import BadRequestHandler
from response.HelpHandler import HelpHandler
from response.RequestHandler import RequestHandler
from config.Config import Config
import glob
import importlib
import logging
from typing import List

import base64


class Server(BaseHTTPRequestHandler):

    def do_HEAD(self):
        return

    def do_GET(self):
        server: PyRSSWHTTPServer = self.server
        if self.checkAuth(self.headers, server.auth_key):
            module_name = self._parseModuleName()
            handler = None

            if module_name == "":  # root page
                handler = HelpHandler(server.handlers)
            else:
                for h in server.handlers:  # find handler from module_name
                    if h.handlerName == module_name:
                        handler = h
                        break

            if handler is None:
                logging.getLogger().error("handler '%s' NOT found" % module_name)
                handler = BadRequestHandler(self.path)
            else:
                handler.process(self.path[len(module_name)+1:])

            self.respond({'handler': handler})

        else:
            logging.getLogger().error("Invalid credentials")
            self.send_response(401)
            self.send_header("WWW-Authenticate", "Basic realm=\"PyRSSW Realm\"")
            self.send_header("Content-type", "application/json")
            self.end_headers()


    def checkAuth(self, headers, auth_key):
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

    def _parseModuleName(self):
        module_name = ""
        split_path = self.path.split('/')
        if len(split_path) > 1:
            module_name = split_path[1]
            if module_name.find('?') > -1:
                module_name = module_name.split('?')[0]

        return module_name

    def handle_http(self, handler):
        content = None
        status_code = handler.getStatus()

        self.send_response(status_code)

        if status_code != 401:
            if status_code == 200:
                content = handler.getContents()
                self.send_header('Content-type', handler.getContentType())
            elif handler.getContents() != "":
                content = handler.getContents()
            else:
                content = "404 Not Found"

        self.end_headers()

        if not content is None:
            if isinstance(content, bytes):
                return content
            else:
                return bytes(content, 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['handler'])
        self.wfile.write(response)


class PyRSSWHTTPServer(HTTPServer):
    def __init__(self, config: Config):
        self.config = config
        super().__init__((config.getServerListeningHostName(),
                          config.getServerListeningPort()), Server)

        if self.getProtocol() == "https":
            self.socket = ssl.wrap_socket(self.socket,
                                          keyfile=config.getKeyFile(),
                                          certfile=config.getCertFile(),
                                          server_side=True)
        # load handlers
        self._loadHandlers()

        self._loadAuthKey()

    def _loadAuthKey(self):
        self.auth_key = None
        login, password = self.config.getBasicAuthCredentials()
        if not login is None and not password is None:
            self.auth_key = base64.b64encode(
                bytes('%s:%s' % (login, password), 'utf-8')).decode('ascii')
        else:
            logging.getLogger().info("No basic auth credentials defined in config.ini")

    def _loadHandlers(self):
        self.handlers: List[RequestHandler] = []
        for handler in glob.glob("response/*Handler.py"):

            moduleName = ".%s" % os.path.basename(handler).strip(".py")
            module = importlib.import_module(
                moduleName, package="response")
            if hasattr(module, 'PyRSSWRequestHandler'):
                self.handlers.append(module.PyRSSWRequestHandler(
                    self.getServingURLPrefix()))

    def getConfig(self) -> Config:
        return self.config

    def getProtocol(self) -> str:
        protocol = "http"
        if not self.config.getKeyFile() is None and not self.config.getCertFile() is None:
            protocol = "https"

        return protocol

    def getListeningURLPrefix(self):
        return "%s://%s:%d" % (
            self.getProtocol(),
            self.config.getServerListeningHostName(),
            self.config.getServerListeningPort())

    def getServingURLPrefix(self):
        return "%s://%s:%d" % (
            self.getProtocol(),
            self.config.getServerServingHostName(),
            self.config.getServerListeningPort())
