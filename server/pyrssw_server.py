import base64
import logging
import ssl
from http.server import HTTPServer
from typing import Optional

from config.config import Config
from server.abstract_pyrssw_server import AbstractPyRSSWHTTPServer
from server.http_request_handler import HTTPRequestHandler


class PyRSSWHTTPServer(HTTPServer, AbstractPyRSSWHTTPServer):
    """HTTP server overriding the basic HTTPServer.
    This class using configuration to apply listening host, port and protocol and also to build the basic auth key if needed.
    """

    def __init__(self):
        super().__init__((Config.instance().get_server_listening_hostname(),
                          Config.instance().get_server_listening_port()), HTTPRequestHandler)

        if self.get_protocol() == "https":
            self.socket = ssl.wrap_socket(self.socket,
                                          keyfile=Config.instance().get_key_file(),
                                          certfile=Config.instance().get_cert_file(),
                                          server_side=True)
        self._load_auth_key()

    def _load_auth_key(self):
        self.auth_key: Optional[str] = None
        login, password = Config.instance().get_basic_auth_credentials()
        if not login is None and not password is None:
            self.auth_key = base64.b64encode(
                bytes('%s:%s' % (login, password), 'utf-8')).decode('ascii')
        else:
            logging.getLogger().info("No basic auth credentials defined in config.ini")

    def get_protocol(self) -> str:
        protocol = "http"
        if not Config.instance().get_key_file() is None and not Config.instance().get_cert_file() is None:
            protocol = "https"

        return protocol

    def get_listening_url_prefix(self):
        return "%s://%s:%d" % (
            self.get_protocol(),
            Config.instance().get_server_listening_hostname(),
            Config.instance().get_server_listening_port())

    def get_serving_url_prefix(self) -> str:
        return "%s://%s:%d" % (
            self.get_protocol(),
            Config.instance().get_server_serving_hostname(),
            Config.instance().get_server_listening_port())

    def get_auth_key(self) -> Optional[str]:
        return self.auth_key
