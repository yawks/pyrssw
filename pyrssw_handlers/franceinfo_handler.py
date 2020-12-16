import re
from typing import cast

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath


class FranceInfoHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.franceinfo.fr">France Info</a> website.

    Handler name: franceinfo

    RSS parameters:
     - filters : politique, faits-divers, societe, economie, monde, culture, sports, sante, environnement, ...

       to invert filtering, prefix it with: ^
       eg :
         - /franceinfo/rss?filter=politique            #only feeds about politique
         - /franceinfo/rss?filter=politique,societe    #only feeds about politique and societe
         - /franceinfo/rss?filter=^politique,societe   #all feeds but politique and societe

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    @staticmethod
    def get_handler_name() -> str:
        return "franceinfo"

    def get_original_website(self) -> str:
        return "http://www.franceinfo.fr/"

    def get_rss_url(self) -> str:
        return "http://www.franceinfo.fr/rss.xml"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "link[contains(text(), '/%s/')]", "not(link[contains(text(), '/%s/')])")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        for link in xpath(dom, "//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": cast(str, link.text).strip()})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        page = session.get(url=url)
        content = page.text.replace(">", ">\n")

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace(
            "data-src", "style='height:100%;width:100%' src")
        dom = etree.HTML(content)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "block-share")]',
            '//*[@id="newsletter-onvousrepond"]',
            '//*[contains(@class, "partner-block")]',
            '//*[contains(@class, "a-lire-aussi")]',
            '//aside[contains(@class, "tags")]',
            '//*[contains(@class, "breadcrumb")]',
            '//*[contains(@class, "col-left")]',
            '//*[contains(@class, "col-right")]',
            '//*[contains(@class, "social-aside")]',  # france3 regions
            '//*[contains(@class, "aside-img__content")]',  # france3 regions
            # france3 regions
            '//*[contains(@class, "social-button-content")]',
            '//*[contains(@class, "tags-button-content")]',  # france3 regions
            '//*[contains(@class, "article-share")]',  # france3 regions
            # france3 regions
            '//*[contains(@class, "article-share-fallback")]',
            # france3 regions
            '//*[contains(@class, "article-share-fallback")]',
            '//*[contains(@class, "related-content")]',
            '//*[contains(@class, "article__thematics")]',
            '//*[contains(@class, "article__related ")]'
        ])

        content = utils.dom_utils.get_content(
            dom, ['//div[contains(@class,"article-detail-block")]',
                  '//article[contains(@id,"node")]',  # france3 regions
                  '//main[contains(@class,"article")]',  # france3 regions
                  '//article[contains(@class,"content-live")]',  # live
                  '//div[contains(@class, "content")]',
                  # sport.francetvinfo.fr
                  '//*[contains(@class,"article-detail-block")]'])

        if len(content.replace("\n", "").strip()) < 150:
            # less than 150 chars, we did not manage to get the content, use readability facility
            content = super().get_readable_content(url)

        return content
