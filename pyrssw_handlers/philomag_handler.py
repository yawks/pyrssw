from request.pyrssw_content import PyRSSWContent
import re
from typing import Dict

import requests
from lxml import etree

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import get_all_contents, text, to_string, xpath, get_content


class PhilomagHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.philomag.com">Philomag</a> website.

    Handler name: philomag

    Content:
        Get content of the page, removing paywall, menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "http://www.philomag.com/"

    def get_rss_url(self) -> str:
        return "https://www.philomag.com/rss-le-fil"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.philomag.com/sites/default/files/favicon_1.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        dom = etree.fromstring(feed.encode("utf-8"))

        for link in xpath(dom, "//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": text(link).strip()})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url)
        dom = etree.HTML(page.text, parser=None)

        seemore = xpath(dom, '//*[contains(@class, "see-more")]')
        if len(seemore) > 0:
            url = seemore[0].attrib["href"]
            if url.startswith("/"):
                url = self.get_original_website() + url[1:]
            page = session.get(url=url)
            dom = etree.HTML(page.text, parser=None)
        
        title = get_content(dom, ["//h1"])
        h1s = xpath(dom, "//h1")
        if len(h1s) > 0:
            h1s[0].getparent().remove(h1s[0])

        content, _ = get_all_contents(
            dom, ['//*[@id="adjustHeader"]', '//*[@id="block-philomag-content"]'])

        return PyRSSWContent(title + content, """
        """)
