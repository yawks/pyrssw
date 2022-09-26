import re
from urllib.parse import quote_plus, urlparse
from request.pyrssw_content import PyRSSWContent
from typing import Dict, cast
import requests
from lxml import etree
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
import favicon
from ftfy import fix_text
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
     - rssurl: url of the target RSS


    Content:
        Get readable content of the target article content
    """

    def get_original_website(self) -> str:
        return ""

    def get_rss_url(self) -> str:
        return ""

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        url = parameters.get("rssurl", parameters.get("url", ""))
        urlp = urlparse(url)
        favicon_url = ""

        def get_favicon(url: str) -> str:
            larger_favicon_url = ""
            larger_favicon_width = 0
            for fav in favicon.get(url):
                    if requests.head(fav.url).status_code == 200 and fav.width >= larger_favicon_width:
                        larger_favicon_url = fav.url
                        larger_favicon_width = fav.width
            
            return larger_favicon_url

        if urlp.hostname is not None:
            try:
                favicon_url = get_favicon("%s://%s" % (urlp.scheme, urlp.hostname))
            except:
                feed = requests.get(url).text
                dom = etree.fromstring(feed.encode("utf-8"))
                site_urls = xpath(dom, "//link")
                if len(site_urls) > 0:
                    favicon_url = get_favicon(cast(str,site_urls[0].text))


        return favicon_url

    def get_handler_name(self, parameters: Dict[str, str]):
        site_name = ""
        urlp = urlparse(parameters.get("rssurl", parameters.get("url", "")))
        if urlp.hostname is not None:
            site_name = urlp.hostname
            html = requests.get("%s://%s" % (urlp.scheme, urlp.hostname)).text
            dom = etree.HTML(html, parser=None)
            site_names = xpath(dom, '//meta[@property="og:site_name"]')
            if len(site_names) > 0:
                site_name = site_names[0].attrib.get("content", urlp.hostname)
        
        return site_name

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = ""
        if "rssurl" in parameters:
            feed = fix_text(session.get(url=parameters["rssurl"], headers={}).text)
            feed = feed.replace(
                '<guid isPermaLink="false">', '<link>')  # NOSONAR
            feed = feed.replace('<guid isPermaLink="true">', '<link>')
            feed = feed.replace('<guid>',' <link>')
            feed = feed.replace('</guid>', '</link>')

            #f eed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
            dom = etree.fromstring(feed.encode("utf-8"))
            
            for item in xpath(dom, "//item"):
                for link in xpath(item, ".//link"):
                    link.text = f"{self.url_prefix}?url={quote_plus(cast(str, link.text))}"
            
            feed = to_string(dom)

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