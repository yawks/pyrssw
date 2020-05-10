import base64
import glob
import importlib
import inspect
import logging
import os
import ssl
from http.server import HTTPServer
from typing import List, Optional

from typing_extensions import Type

from config.config import Config
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from handlers.request_handler import RequestHandler
from server.abstract_pyrssw_server import AbstractPyRSSWHTTPServer
from server.http_request_handler import HTTPRequestHandler


class PyRSSWHTTPServer(HTTPServer, AbstractPyRSSWHTTPServer):
    """HTTP server overriding the basic HTTPServer.
    This class has 2 purposers:
        - using configuration to apply listening host, port and protocol and also to build the basic auth key if needed.
        - loading all handlers in order to provide them to any incoming queries.
    """

    def __init__(self, config: Config):
        self.config = config
        super().__init__((config.get_server_listening_hostname(),
                          config.get_server_listening_port()), HTTPRequestHandler)

        if self.get_protocol() == "https":
            self.socket = ssl.wrap_socket(self.socket,
                                          keyfile=config.get_key_file(),
                                          certfile=config.get_cert_file(),
                                          server_side=True)
        self._load_handlers()
        self._load_auth_key()

    def _load_auth_key(self):
        self.auth_key: Optional[str] = None
        login, password = self.config.get_basic_auth_credentials()
        if not login is None and not password is None:
            self.auth_key = base64.b64encode(
                bytes('%s:%s' % (login, password), 'utf-8')).decode('ascii')
        else:
            logging.getLogger().info("No basic auth credentials defined in config.ini")

    def _load_handlers(self):
        self.handlers: List[Type[PyRSSWRequestHandler]] = []
        for handler in glob.glob("pyrssw_handlers/*.py"):
            module_name = ".%s" % os.path.basename(handler).strip(".py")
            module = importlib.import_module(module_name, package="pyrssw_handlers")
            if hasattr(module, "PyRSSWRequestHandler") and not hasattr(module, "ABC"):
                for member in inspect.getmembers(module):
                    if member[0].find("__") == -1 and isinstance(member[1], type) and issubclass(member[1], getattr(module, "PyRSSWRequestHandler")) and member[1].__name__ != "PyRSSWRequestHandler":
                        # do not add the abstract class in the handlers list and avoid native types

                        self._load_handler(member)

    def _load_handler(self, member):
        try:
            member[1]() #just try to instanciate to check if everything is ok
        except Exception as e:
            logging.getLogger().error("Error instanciating the class '%s' : %s" % (member[0], str(e)))

        self.handlers.append(member[1])

    def get_config(self) -> Config:
        return self.config

    def get_protocol(self) -> str:
        protocol = "http"
        if not self.config.get_key_file() is None and not self.config.get_cert_file() is None:
            protocol = "https"

        return protocol

    def get_listening_url_prefix(self):
        return "%s://%s:%d" % (
            self.get_protocol(),
            self.config.get_server_listening_hostname(),
            self.config.get_server_listening_port())

    def get_serving_url_prefix(self) -> str:
        return "%s://%s:%d" % (
            self.get_protocol(),
            self.config.get_server_serving_hostname(),
            self.config.get_server_listening_port())

    def get_auth_key(self) -> Optional[str]:
        return self.auth_key

    def get_handlers(self) -> List[Type[PyRSSWRequestHandler]]:
        return self.handlers
    
    def get_crypto_key(self) -> bytes:
        return self.config.get_crypto_key()
