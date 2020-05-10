import logging
import socket
from typing import Dict, Optional, Tuple

from cryptography.fernet import Fernet

DEFAULT_HOST_NAME = socket.gethostbyaddr(socket.gethostname())[0]
DEFAULT_PORT_NUMBER = 8001

SERVER_LISTENING_HOSTNAME_KEY = "server.listening_hostname"
SERVER_LISTENING_PORT_KEY = "server.listening_port"
SERVER_KEYFILE_KEY = "server.keyfile"
SERVER_CERTFILE_KEY = "server.certfile"
SERVER_BASICAUTH_LOGIN_KEY = "server.basicauth.login"
SERVER_BASICAUTH_PASSWORD_KEY = "server.basicauth.password"
SERVER_SERVING_HOSTNAME_KEY = "server.serving_hostname"
SERVER_CRYPTO_KEY = "server.crypto_key"


class Config:
    """handle the optional config file"""

    def __init__(self, config_file: str):
        self.configuration: Dict[str, str] = {}
        self.config_file: str = config_file
        if config_file != "":
            self.configuration = self.load_properties()

    def load_properties(self, sep: str = '=', comment_char: str = '#', section_char: str = '[') -> dict:
        # credits: https://stackoverflow.com/questions/3595363/properties-file-in-python-similar-to-java-properties
        props = {}
        with open(self.config_file, "rt") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith(comment_char) and not l.startswith(section_char):
                    key_value = l.split(sep)
                    key = key_value[0].strip()
                    value = sep.join(key_value[1:]).strip().strip('"')
                    props[key] = value
        return props

    def get_server_listening_hostname(self) -> str:
        server_host_name = DEFAULT_HOST_NAME
        if SERVER_LISTENING_HOSTNAME_KEY in self.configuration and self.configuration[SERVER_LISTENING_HOSTNAME_KEY] != '':
            server_host_name = self.configuration[SERVER_LISTENING_HOSTNAME_KEY]

        return server_host_name

    def get_server_listening_port(self) -> int:
        server_port = DEFAULT_PORT_NUMBER
        if SERVER_LISTENING_PORT_KEY in self.configuration and (self.configuration[SERVER_LISTENING_PORT_KEY]).isdigit():
            server_port = int(self.configuration[SERVER_LISTENING_PORT_KEY])

        return server_port

    def get_key_file(self) -> Optional[str]:
        key_file = None
        if SERVER_KEYFILE_KEY in self.configuration:
            key_file = self.configuration[SERVER_KEYFILE_KEY]

        return key_file

    def get_cert_file(self) -> Optional[str]:
        cert_file = None
        if SERVER_CERTFILE_KEY in self.configuration:
            cert_file = self.configuration[SERVER_CERTFILE_KEY]

        return cert_file

    def get_server_serving_hostname(self) -> str:
        server_hostname = self.get_server_listening_hostname()
        if SERVER_SERVING_HOSTNAME_KEY in self.configuration and self.configuration[SERVER_SERVING_HOSTNAME_KEY] != '':
            server_hostname = self.configuration[SERVER_SERVING_HOSTNAME_KEY]

        return server_hostname

    def get_basic_auth_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        login = None
        password = None
        if SERVER_BASICAUTH_LOGIN_KEY in self.configuration and SERVER_BASICAUTH_PASSWORD_KEY and self.configuration[SERVER_BASICAUTH_LOGIN_KEY] != '' and self.configuration[SERVER_BASICAUTH_PASSWORD_KEY] != '':
            login = self.configuration[SERVER_BASICAUTH_LOGIN_KEY]
            password = self.configuration[SERVER_BASICAUTH_PASSWORD_KEY]

        return login, password

    def get_crypto_key(self) -> bytes:
        if not SERVER_CRYPTO_KEY in self.configuration or self.configuration[SERVER_CRYPTO_KEY] == '':
            # automatically writes a crypto key
            logging.getLogger().info("No %s defined, creating one and add it to the %s file" %
                                     (SERVER_CRYPTO_KEY, self.config_file))
            crypto_key = Fernet.generate_key()
            f = open(self.config_file, "a")
            f.write("\n%s=%s" % (SERVER_CRYPTO_KEY, crypto_key.decode('ascii')))
        else:
            crypto_key = self.configuration[SERVER_CRYPTO_KEY].encode('ascii')

        return crypto_key
