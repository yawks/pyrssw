from request.pyrssw_content import PyRSSWContent
import re
from typing import cast

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath


class CourrierInternationalHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.courrierinternational.fr">Courrier International</a> website.

    Handler name: courrierinternational

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "http://www.courrierinternational.fr/"

    def get_rss_url(self) -> str:
        return "https://www.courrierinternational.com/feed/all/rss.xml"

    @staticmethod
    def get_favicon_url() -> str:
        return "https://www.courrierinternational.com/bucket/90bfeb04e74422b89ea0427235fa82404b2ab1b0/img/logos/favicon.ico"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)

        for link in xpath(dom, "//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": cast(str, link.text).strip()})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url)
        content = page.text.replace(">", ">\n")

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace(
            "data-src", "style='height:100%;width:100%' src")
        dom = etree.HTML(content)

        utils.dom_utils.delete_xpaths(dom, [
            '//div[contains(@class, "article-metas")]',
            '//div[contains(@class,"article-secondary")]',
            '//aside[contains(@class,"article-tools")]'
        ])

        header = utils.dom_utils.get_content(
            dom, ['//header[@class="article-header"]'])
        
        body = utils.dom_utils.get_content(
            dom, ['//div[@class="article-content"]'])

        content = header + body

        if len(content.replace("\n", "").strip()) < 150:
            # less than 150 chars, we did not manage to get the content, use readability facility
            content = super().get_readable_content(session, url)

        
        return PyRSSWContent(content, """
            #courrierinternational_handler h1 {display:inline}
            #courrierinternational_handler span.strapline {color: #ff7d24;font-weight: 500;}
            #courrierinternational_handler .article-heading span.strapline {font-size: 170%;}
            #courrierinternational_handler .article-header ul {list-style:none;padding:0;margin:0}
            #courrierinternational_handler li {display: inline-block;text-transform: uppercase;font-size: 14px;letter-spacing: 2px;}
            #courrierinternational_handler .article-header .item:not(:last-child):after {content: "\\A0\\2022\\A0";font-weight: 600;}
            #courrierinternational_handler a, a:any-link {--siteText: var(--siteText);text-decoration: none;color: inherit;outline: 0;}
            #courrierinternational_handler a:hover {text-decoration: underline;}
        """)
