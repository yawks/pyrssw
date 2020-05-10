from abc import ABCMeta, abstractmethod
from typing import Optional

from cryptography.fernet import Fernet


class PyRSSWRequestHandler(metaclass=ABCMeta):

    def __init__(self, fernet: Fernet, url_prefix: Optional[str] = ""):
        self.url_prefix = url_prefix
        self.fernet = fernet

    def encrypt(self, value) -> str:
        return self.fernet.encrypt(value.encode("ascii")).decode('ascii')

    @classmethod
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
    def get_feed(self, parameters: dict) -> str:
        """Takes a dictionary of parameters and must return the xml of the rss feed

        Arguments:
            parameters {dict} -- list of parameters

        Returns:
            str -- the xml feed
        """

    @abstractmethod
    def get_content(self, url: str, parameters: dict) -> str:
        """Takes an url and a dictionary of parameters and must return the result content.

        Arguments:
            url {str} -- url of the original content
            parameters {dict} -- list of parameters (darkmode, login, password, ...)

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
