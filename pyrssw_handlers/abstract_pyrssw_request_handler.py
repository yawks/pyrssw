from abc import ABCMeta, abstractmethod
import datetime
import logging
import re
from lxml import etree
from utils.dom_utils import get_first_node, text, to_string, xpath
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
            self.get_handler_name({}),
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

    def get_readable_content(self, session: requests.Session, url: Optional[str], headers: Dict[str, str] = {}, add_source_link=False, add_title=True) -> str:
        """Return the readable content of the given url

        Args:
            url (str): The content to retrieve URL
            add_source_link (bool, optional): To add at the beginning of the content source and a link. Defaults to False.
            add_title (bool, optional): True by default. Add the article title as h1. If False, no title.

        Returns:
            str: [description]
        """
        readable_content: str = ""
        if url is not None and is_url_valid(url):
            try:
                r = session.get(cast(str, url), headers=headers, verify=False)

                html = fix_text(r.text)
                if html is not None and html.strip() != "":
                    dom = etree.HTML(html, parser=None)
                    url_prefix = url[:len("https://") +
                                     len(url[len("https://"):].split("/")[0])+1]
                    noticeable_imgs = _get_noticeable_imgs(dom, url_prefix)
                    new_html = to_string(dom)

                    doc = Document(new_html.replace("width", "_width_").replace(
                        "height", "_height_"))

                    if add_source_link:
                        readable_content += "<hr/><p><u><a href=\"%s\">Source</a></u> : %s</p><hr/>" % (
                            url, url_prefix)

                    summary = doc.summary(html_partial=True).replace(
                        "_width_", "width").replace("_height_", "height")

                    if add_title:
                        readable_content = _complete_with_h1(dom, summary)

                    for img in noticeable_imgs:
                        if img not in summary:
                            readable_content += "<p><img style=\"min-width:100%%\" src=\"%s\"></img></p>" % img

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
            except Exception as e:
                readable_content = f"Error getting <i><a href='{url}'>{url}</a></i><br/> <pre>{e}</pre>"

        return readable_content


def _get_noticeable_imgs(dom: etree.HTML, url_prefix: str) -> List[str]:
    """find in html all 'noticeable' images, which means quite big enough to be considered useful.

    Args:
        dom (etree): html dom
        url_prefix (str): url prefix

    Returns:
        List[str]: list of images urls found as noticeable
    """
    noticeable_imgs: List[str] = []

    def _get_width(node: etree.Element):
        width = 0
        if str.isdigit(node.attrib.get("width", "")):
            width = int(node.attrib.get("width", ""))
        elif "width:" in node.attrib.get("style", ""):
            styles = node.attrib.get("style", "").split(";")
            for style in styles:
                if style.find("width:") == 0:
                    width = int(re.sub("[^0-9]", "", style.split(":")[1]))
                    break

        return width

    for node in xpath(dom, "//img"):
        if _get_width(node) > 500:
            attr_name = "src"
            for attr in node.attrib:  # handle lazyload img attributes
                if attr.endswith("-src") or attr.find("-src-") > -1:
                    attr_name = attr
                    break
            src = cast(str, node.attrib.get(attr_name, ""))
            if src[0:1] not in ("h", "/"):
                src = url_prefix + src
                node.attrib[attr_name] = src
            """
            i f src == "":
                for attr in node.attrib: #handle lazyload img attributes
                    if attr.find("-src") > -1 and "http" in node.attrib[attr]:
                        idx_start = node.attrib[attr].find("http")
                        idx_end = node.attrib[attr][idx_start:].find(" ")
                        if idx_end == -1:
                            idx_end = len(node.attrib[attr])
                        src = node.attrib[attr][idx_start:idx_end]
                        attr_name = attr
                        break
            """
            if src != "" and (is_url_valid(src) or node.attrib[attr_name][:1] == "/") and src not in noticeable_imgs:
                img_node = node
                ref_node = node.getparent()
                n = node
                while n is not None:
                    if n.tag in ["dt", "aside", "dl", "dd"]:
                        ref_node = n
                    n = n.getparent()

                if ref_node.tag != "p":
                    p = etree.Element("p")
                    ref_node.addprevious(p)
                    img_node.getparent().remove(img_node)
                    p.append(img_node)

                noticeable_imgs.append(src)

    return noticeable_imgs


def _complete_with_h1(dom: etree.HTML, summary: str) -> str:
    h1_content = ""
    h1 = get_first_node(dom, ["//article//h1"])
    if h1 is None:
        h1 = get_first_node(dom, ["//h1"])
    if h1 is not None:
        h1_str = re.sub('\s+(?=<)', '', to_string(h1))
        if h1_str.strip() != "":
            h1_content = h1_str

    if h1_content in re.sub('\s+(?=<)', '', summary):
        h1_content = ""
    elif h1_content == "":
        # if nothing found in h1, take a look in the title of the page
        title = get_first_node(dom, ["//head//title"])
        if title is not None and text(title) != "":
            h1_content = "<h1>%s</h1>" % text(title)

    return h1_content
