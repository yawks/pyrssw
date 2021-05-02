from abc import ABCMeta, abstractmethod
import datetime
import logging
import re
import itertools
from utils.url_utils import is_url_valid
from request.pyrssw_content import PyRSSWContent
from typing import Dict, Optional, cast
from urllib.parse import quote_plus
from readability import Document
from ftfy import fix_text

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
                hasattr(subclass, "get_rss_url") and
                callable(subclass.get_rss_url) and
                hasattr(subclass, "get_favicon_url") and
                callable(subclass.get_favicon_url)
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
    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        """Takes an url and a dictionary of parameters and must return the result content.

        Arguments:
            url {str} -- url of the original content
            parameters {dict} -- list of parameters (darkmode, login, password, ...)
            parameters {requests.Session} -- the session provided to process HTTP queries

        Returns:
            PyRSSWContent -- the content reworked
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

    def get_handler_name_for_url(self) -> str:
        return type(self).__name__.replace("Handler", "").lower()

    def get_handler_name(self) -> str:
        """Returns the handler name

        Returns:
            str -- handler name
        """
        return re.sub(r"([A-Z])", r" \1", type(self).__name__.replace("Handler", "")).strip()

    @staticmethod
    @abstractmethod
    def get_favicon_url() -> str:
        """Return the favicon url

        Returns:
            str: favicon url
        """

    def get_readable_content(self, session: requests.Session, url: Optional[str], headers: Dict[str, str] = {}, add_source_link=False) -> str:
        """Return the readable content of the given url

        Args:
            url (str): The content to retrieve URL
            add_source_link (bool, optional): To add at the beginning of the content source and a link. Defaults to False.

        Returns:
            str: [description]
        """
        readable_content: str = ""
        if is_url_valid(url):
            r = session.get(cast(str, url), headers=headers)
            doc = Document(r.text)
            url_prefix = url[:len("https://") +
                             len(url[len("https://"):].split("/")[0])+1]

            if add_source_link:
                readable_content += "<hr/><p><u><a href=\"%s\">Source</a></u> : %s</p><hr/>" % (
                    url, url_prefix)
            readable_content += fix_text(doc.summary())
            readable_content = readable_content.replace("<html>", "").replace(
                "</html>", "").replace("<body>", "").replace("</body>", "")

            # replace relative links
            readable_content = readable_content.replace(
                'href="/', 'href="' + url_prefix)
            readable_content = readable_content.replace(
                'src="/', 'src="' + url_prefix)
            readable_content = readable_content.replace(
                'href=\'/', 'href=\'' + url_prefix)
            readable_content = readable_content.replace(
                'src=\'/', 'src=\'' + url_prefix)
            readable_content = readable_content.replace(
                "<noscript>", "").replace("</noscript>", "")

            """
            Not sure still useful with fix_text
            if readable_content.find("\x92") > -1 or readable_content.find("\x96") > -1 or readable_content.find("\xa0") > -1:
                #fix enconding stuffs
                try:
                    readable_content = readable_content.encode("latin1").decode("cp1252")
                except UnicodeEncodeError:
                    pass
            """

        return readable_content
