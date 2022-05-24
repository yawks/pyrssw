from request.pyrssw_content import PyRSSWContent
import re
from typing import Dict, cast

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath


class GenericWrapperHandler(PyRSSWRequestHandler):
    """Handler for any website.
    The purpose of this handler is to enrich any rss feed with pyrssw features and provide readable content for articles:
     - dark mode
     - font size
     - twitter links integrated
     - ...

    Handler name: genericwrapper

    RSS parameters:
     - rssurl : url of the target RSS


    Content:
        Get readable content of the target article content
    """

    def get_original_website(self) -> str:
        return ""

    def get_rss_url(self) -> str:
        return ""

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        favicon = ""
        if "rssurl" in parameters:
            feed = requests.get(url=parameters["rssurl"], headers={}).text
            feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
            dom = etree.fromstring(feed)
            images = xpath(dom, "//channel/image/url")
            if len(images) > 0:
                favicon = images[0].text

        return favicon

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = ""
        if "rssurl" in parameters:
            feed = session.get(url=parameters["rssurl"], headers={}).text
            feed = feed.replace(
                '<guid isPermaLink="false">', '<link>')  # NOSONAR
            feed = feed.replace('<guid isPermaLink="true">', '<link>')
            feed = feed.replace('</guid>', '</link>')
            feed = feed.replace('<link>', '<link>%s?url=' % self.url_prefix)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        return PyRSSWContent(self.get_readable_content(session, url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Cache-Control": "no-cache",
            "Content-Encoding": "identity",
            "Accept-Charset": "utf-8",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
            "Connection": "keep-alive",
            "Pragma": "no-cache"
        }), "")
