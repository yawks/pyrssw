from abc import ABCMeta, abstractmethod
import datetime
import logging
import re
from lxml import etree
from utils.dom_utils import get_first_node, xpath
from utils.url_utils import is_url_valid
from request.pyrssw_content import PyRSSWContent
from typing import Dict, List, Optional, cast
from urllib.parse import quote_plus
from utils.readability import Document
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

    def get_handler_name(self, parameters: Dict[str, str]) -> str:
        """Returns the handler name

        Args:
            parameters (Dict[str, str]): feed parameters
        Returns:
            str -- handler name
        """
        return re.sub(r"([A-Z])", r" \1", type(self).__name__.replace("Handler", "")).strip()

    @staticmethod
    @abstractmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
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
        if url is not None and is_url_valid(url):
            r = session.get(cast(str, url), headers=headers)

            html = fix_text(r.text)
            doc = Document(html.replace("width", "_width_").replace(
                "height", "_height_"))

            url_prefix = url[:len("https://") +
                             len(url[len("https://"):].split("/")[0])+1]

            if add_source_link:
                readable_content += "<hr/><p><u><a href=\"%s\">Source</a></u> : %s</p><hr/>" % (
                    url, url_prefix)

            summary = doc.summary(html_partial=True).replace("_width_", "width").replace("_height_", "height")
            dom = etree.HTML(html, parser=None)
            h1 = get_first_node(dom, ["//h1"])
            if h1 is not None and h1.text not in summary:
                readable_content += "<h1>%s</h1>" % h1.text

            noticeable_imgs = _get_noticeable_imgs(dom)
            for img in noticeable_imgs:
                if img not in summary:
                    readable_content += "<img style=\"min-width:100%%\" src=\"%s\"></img>" % img

            readable_content += summary

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


        return readable_content


def _get_noticeable_imgs(dom: etree.HTML) -> List[str]:
    """find in html all 'noticeable' images, which means quite big enough to be considered useful.

    Args:
        dom (etree): html dom

    Returns:
        List[str]: list of images urls found as noticeable
    """
    noticeable_imgs: List[str] = []

    for node in xpath(dom, "//img"):
        if str.isdigit(node.attrib.get("width", "")) and int(node.attrib.get("width", "")) > 500:
            for attr in node.attrib:
                if attr.find("src") > -1 and is_url_valid(node.attrib[attr]) and node.attrib[attr] not in noticeable_imgs:
                    noticeable_imgs.append(node.attrib[attr])

    return noticeable_imgs
