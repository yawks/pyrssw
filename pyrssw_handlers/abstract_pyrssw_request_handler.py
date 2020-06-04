import datetime
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import Dict, Optional
from urllib.parse import quote_plus

import requests
from cryptography.fernet import Fernet

# this prefix is added to encrypted values to help the url parameters finder knowing which parameters must be decrypted
ENCRYPTED_PREFIX = "!e:"


class PyRSSWRequestHandler(metaclass=ABCMeta):

    def __init__(self, fernet: Optional[Fernet] = None, url_prefix: Optional[str] = "", source_ip: Optional[str] = ""):
        self.url_prefix: Optional[str] = url_prefix
        self.fernet = fernet
        self.logger = logging.getLogger()
        self.source_ip: Optional[str] = source_ip

    def encrypt(self, value) -> str:
        return "%s%s" % (ENCRYPTED_PREFIX, self.fernet.encrypt(value.encode("ascii")).decode('ascii'))

    def log_info(self, msg):
        self.logger.info(self._get_formatted_msg(msg))

    def log_error(self, msg):
        self.logger.error(self._get_formatted_msg(msg))

    def _get_formatted_msg(self, msg):
        return "[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] [%s] - %s - %s" % (
            self.get_handler_name(),
            self.source_ip,
            re.sub("%s[^\\s&]*" % ENCRYPTED_PREFIX, "XXXX", msg)
        )  # anonymize crypted params in logs

    def get_handler_url_with_parameters(self, parameters: Dict[str, str]) -> str:
        url_with_parameters: str = ""
        if self.url_prefix is not None:
            url_with_parameters = self.url_prefix
            for key in parameters:
                if url_with_parameters == self.url_prefix:
                    url_with_parameters += "?"
                else:
                    url_with_parameters += "&"
                url_with_parameters += "%s=%s" % (key,
                                                  quote_plus(parameters[key]))

        return url_with_parameters

    @ classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, "get_original_website") and
                callable(subclass.get_original_website) and
                hasattr(subclass, "get_feed") and
                callable(subclass.get_feed) and
                hasattr(subclass, "get_content") and
                callable(subclass.get_content) and
                hasattr(subclass, "get_handler_name") and
                callable(subclass.get_handler_name) and
                hasattr(subclass, "get_rss_url") and
                callable(subclass.get_rss_url)
                or NotImplemented)

    @abstractmethod
    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        """Takes a dictionary of parameters and must return the xml of the rss feed

        Arguments:
            parameters {dict} -- list of parameters
            parameters {requests.Session} -- the session provided to process HTTP queries

        Returns:
            str -- the xml feed
        """

    @abstractmethod
    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        """Takes an url and a dictionary of parameters and must return the result content.

        Arguments:
            url {str} -- url of the original content
            parameters {dict} -- list of parameters (darkmode, login, password, ...)
            parameters {requests.Session} -- the session provided to process HTTP queries

        Returns:
            str -- the content reworked
        """

    @abstractmethod
    def get_original_website(self) -> str:
        """Returns the original url website

        Returns:
            str -- original url website
        """

    @abstractmethod
    def get_rss_url(self) -> str:
        """Returns the url of the rss feed

        Returns:
            str -- url of the rss feed
        """

    @staticmethod
    @abstractmethod
    def get_handler_name() -> str:
        """Returns the handler name

        Returns:
            str -- handler name
        """
