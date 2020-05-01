import os
import importlib

import ssl
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from response.BadRequestHandler import BadRequestHandler
from response.IziSmileHandler import IzismileHandler
from response.LesJoiesDuCodeHandler import LesJoiesDuCodeHandler
from response.EvilmilkHandler import EvilmilkHandler
from response.EurosportHandler import EurosportHandler
from response.Sport24Handler import Sport24Handler
from response.LeMondeHandler import LeMondeHandler
from response.ThumbnailsHandler import ThumbnailsHandler
from config.Config import Config

import logging


class Server(BaseHTTPRequestHandler):
    def do_HEAD(self):
        return

    def do_GET(self):
        split_path = self.path.split("/")
        module_name = split_path[1]
        # TODO improve that with a dynamic loadings
        if module_name == "izismile":
            handler = IzismileHandler(self.server.getServingURLPrefix())
        elif module_name == "lesjoiesducode":
            handler = LesJoiesDuCodeHandler(self.server.getServingURLPrefix())
        elif module_name == "evilmilk":
            handler = EvilmilkHandler(self.server.getServingURLPrefix())
        elif module_name == "eurosport":
            handler = EurosportHandler(self.server.getServingURLPrefix())
        elif module_name == "sport24":
            handler = Sport24Handler(self.server.getServingURLPrefix())
        elif module_name == "lemonde":
            handler = LeMondeHandler(self.server.getServingURLPrefix())
        elif module_name == "thumbnails":
            handler = ThumbnailsHandler(self.server.getServingURLPrefix())
        else:
            handler = BadRequestHandler(self.server.getServingURLPrefix(), self.path)

        handler.process(self.path[len(module_name)+1:])
        self.respond({
            'handler': handler
        })

    def handle_http(self, handler):
        status_code = handler.getStatus()

        self.send_response(status_code)

        if status_code == 200:
            content = handler.getContents()
            self.send_header(
                'Content-type', handler.getContentType() + '; charset=utf-8')
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
