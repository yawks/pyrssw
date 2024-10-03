import logging
import socket
from typing import Dict, Optional, Tuple, cast
import os.path

from cryptography.fernet import Fernet
from utils.singleton import Singleton

DEFAULT_HOST_NAME = socket.gethostbyaddr(socket.gethostname())[0]
DEFAULT_PORT_NUMBER = 8001

SERVER_LISTENING_HOSTNAME_KEY = "server.listening_hostname"
SERVER_LISTENING_PORT_KEY = "server.listening_port"
SERVER_KEYFILE_KEY = "server.keyfile"
SERVER_CERTFILE_KEY = "server.certfile"
SERVER_BASICAUTH_LOGIN_KEY = "server.basicauth.login"
SERVER_BASICAUTH_PASSWORD_KEY = "server.basicauth.password"
SERVER_SERVING_URL_PREFIX = "server.serving_url_prefix"
SERVER_CRYPTO_KEY = "server.crypto_key"


DEFAULT_CONFIG_FILE = "resources/config.ini"


@Singleton
class Config:
    """handle the optional config file"""

    def __init__(self) -> None:
        self.configuration: Dict[str, str] | None = None
        self.config_file: str = ""

    def load_config_file(self, config_file: str):
        if os.path.isfile(config_file):
            logging.getLogger().debug("Config file '%s' loaded.", config_file)
            self.config_file = config_file
            self.load_properties()
        else:
            logging.getLogger().warning(
                "Config file '%s' not found, default configuration will be used", config_file)

    def _get_configuration(self) -> Dict[str, str]:
        if self.configuration is None:
            self.load_config_file(DEFAULT_CONFIG_FILE)

        return cast(Dict[str, str], self.configuration)

    def load_properties(self, sep: str = '=', comment_char: str = '#'):
        # credits: https://stackoverflow.com/questions/3595363/properties-file-in-python-similar-to-java-properties
        self.configuration = {}
        with open(self.config_file, "rt") as f:
            for line in f:
                line_striped = line.strip()
                if line_striped and not line_striped.startswith(comment_char):
                    key_value = line_striped.split(sep)
                    key = key_value[0].strip()
                    value = sep.join(key_value[1:]).strip().strip('"')
                    self.configuration[key] = value

    def get_server_listening_hostname(self) -> str:
        server_host_name = DEFAULT_HOST_NAME
        if SERVER_LISTENING_HOSTNAME_KEY in self._get_configuration() and self._get_configuration()[SERVER_LISTENING_HOSTNAME_KEY] != '':
            server_host_name = self._get_configuration()[
                SERVER_LISTENING_HOSTNAME_KEY]

        return server_host_name

    def get_server_listening_port(self) -> int:
        server_port = DEFAULT_PORT_NUMBER
        if SERVER_LISTENING_PORT_KEY in self._get_configuration() and (self._get_configuration()[SERVER_LISTENING_PORT_KEY]).isdigit():
            server_port = int(self._get_configuration()[
                              SERVER_LISTENING_PORT_KEY])

        return server_port

    def get_key_file(self) -> Optional[str]:
        key_file = None
        if SERVER_KEYFILE_KEY in self._get_configuration():
            key_file = self._get_configuration()[SERVER_KEYFILE_KEY]

        return key_file

    def get_cert_file(self) -> Optional[str]:
        cert_file = None
        if SERVER_CERTFILE_KEY in self._get_configuration():
            cert_file = self._get_configuration()[SERVER_CERTFILE_KEY]

        return cert_file

    def get_server_serving_url_prefix(self) -> str:
        server_hostname = self.get_server_listening_hostname()
        if SERVER_SERVING_URL_PREFIX in self._get_configuration() and self._get_configuration()[SERVER_SERVING_URL_PREFIX] != '':
            server_hostname = self._get_configuration()[
                SERVER_SERVING_URL_PREFIX]

        return server_hostname
    
    def get_basic_auth_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        login = None
        password = None
        if SERVER_BASICAUTH_LOGIN_KEY in self._get_configuration() and SERVER_BASICAUTH_PASSWORD_KEY and self._get_configuration()[SERVER_BASICAUTH_LOGIN_KEY] != '' \
                and self._get_configuration()[SERVER_BASICAUTH_PASSWORD_KEY] != '':
            login = self._get_configuration()[SERVER_BASICAUTH_LOGIN_KEY]
            password = self._get_configuration()[SERVER_BASICAUTH_PASSWORD_KEY]

        return login, password

    def get_crypto_key(self) -> bytes:
        if SERVER_CRYPTO_KEY not in self._get_configuration() or self._get_configuration()[SERVER_CRYPTO_KEY] == '':
            # automatically writes a crypto key
            logging.getLogger().info("No %s defined, creating one and add it to the %s file",
                                     SERVER_CRYPTO_KEY, self.config_file)
            crypto_key = Fernet.generate_key()
            self.configuration[SERVER_CRYPTO_KEY] = crypto_key.decode("ascii")
            with open(self.config_file, "a") as f:
                f.write("\n\n%s=%s" %
                        (SERVER_CRYPTO_KEY, crypto_key.decode("ascii")))
        else:
            crypto_key = self._get_configuration(
            )[SERVER_CRYPTO_KEY].encode("ascii")

        return crypto_key

    def _get_value(self, key) -> Optional[str]:
        value: Optional[str] = None
        if key in self._get_configuration():
            value = self._get_configuration()[key]
        
        return value