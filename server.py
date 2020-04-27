import os
import importlib

from http.server import BaseHTTPRequestHandler

from response.BadRequestHandler import BadRequestHandler
from response.IziSmileHandler import IzismileHandler
from response.LesJoiesDuCodeHandler import LesJoiesDuCodeHandler
from response.EvilmilkHandler import EvilmilkHandler
from response.EurosportHandler import EurosportHandler

import logging

class Server(BaseHTTPRequestHandler):
    def do_HEAD(self):
        return

    def do_GET(self):
        split_path = self.path.split("/")
        module_name = split_path[1]
        prefix = "http"
        if hasattr(self.server.socket, "keyfile"):
            prefix = "https"
        logging.getLogger().info("prefix:"+prefix)

        #TODO improve that with a dynamic loadings
        if module_name == "izismile":
            handler = IzismileHandler(prefix, self.server.server_name, self.server.server_port)
        elif module_name == "lesjoiesducode":
            handler = LesJoiesDuCodeHandler(prefix, self.server.server_name, self.server.server_port)
        elif module_name == "evilmilk":
            handler = EvilmilkHandler(prefix, self.server.server_name, self.server.server_port)
        elif module_name == "eurosport":
            handler = EurosportHandler(prefix, self.server.server_name, self.server.server_port)
        else:
            handler =  BadRequestHandler(prefix, self.path)
        
        handler.process(self.path[len(module_name)+1:])
        self.respond({
            'handler': handler
        })

    def handle_http(self, handler):
        status_code = handler.getStatus()

        self.send_response(status_code)

        if status_code == 200:
            content = handler.getContents()
            self.send_header('Content-type', handler.getContentType()+ '; charset=utf-8')
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
