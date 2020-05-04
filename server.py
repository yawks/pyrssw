import os
import importlib

import ssl
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from response.BadRequestHandler import BadRequestHandler
from config.Config import Config
import glob
import importlib
import logging


class Server(BaseHTTPRequestHandler):

    def do_HEAD(self):
        return

    def do_GET(self):
        module_name = self._parseModuleName()
        server: RSSHTTPServer = self.server
        handler = None

        for h in server.handlers:  # find handler from module_name
            if h.handlerName == module_name:
                handler = h

        if handler is None:
            handler = BadRequestHandler(
                self.server.getServingURLPrefix(), self.path)

        handler.process(self.path[len(module_name)+1:])
        self.respond({
            'handler': handler
        })

    def _parseModuleName(self):
        module_name = ""
        split_path = self.path.split('/')
        if len(split_path) > 1:
            module_name = split_path[1]
            if module_name.find('?') > -1:
                module_name = module_name.split('?')[0]

        return module_name

    def handle_http(self, handler):
        status_code = handler.getStatus()

        self.send_response(status_code)

        if status_code == 200:
            content = handler.getContents()
            self.send_header('Content-type', handler.getContentType())
        elif handler.getContents() != "":
            content = handler.getContents()
        else:
            content = "404 Not Found"

        self.end_headers()

        if isinstance(content, bytes):
            return content
        else:
            return bytes(content, 'UTF-8')

    def respond(self, opts):
        response = self.handle_http(opts['handler'])
        self.wfile.write(response)


class RSSHTTPServer(HTTPServer):
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
        self.handlers: list = []
        for handler in glob.glob("response/*Handler.py"):
            # do not load generic handlers
            if not handler.endswith("BadRequestHandler.py") and not handler.endswith("RequestHandler.py"):
                moduleName = ".%s" % os.path.basename(handler).strip(".py")
                module = importlib.import_module(
                    moduleName, package="response")
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
