from request.pyrssw_content import PyRSSWContent
import re
from typing import Dict, Optional, cast

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath


class NovethicHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.novethic.fr">Novethic</a> website.

    Handler name: novethic

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.novethic.fr/"

    def get_rss_url(self) -> str:
        return "https://www.novethic.fr/feed"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.novethic.fr/fileadmin/templates/novethic/img/unsprited/icons/favicon-novethic.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        dom = etree.fromstring(feed.encode("utf-8"))

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
            '//footer[contains(@class,"article-footer")]'
        ])

        content = utils.dom_utils.get_content(
            dom, ['//article[contains(@class,"page-articles-fiche")]'])

        if len(content.replace("\n", "").strip()) < 150:
            # less than 150 chars, we did not manage to get the content, use readability facility
            content = super().get_readable_content(session, url)

        return PyRSSWContent(content, """
            #novethic_handler .page-articles-list p, .article-corpsDeTexte ul>li {
                color: #000000;
            }
            #novethic_handler .page-articles-headline-category p {
                margin-top: 0;
                position: relative;
                top: -12px;
                display: inline-block;
                font-size: 17px;
                line-height: 17px;
                text-transform: uppercase;
                color: #232323;
                padding: 8px 20px 6px;

                background-image: -webkit-linear-gradient(top,#1ac6fc 0,#069bc7 100%);
                background-image: linear-gradient(to bottom,#1ac6fc 0,#069bc7 100%);
                background-repeat: repeat-x;
                filter: progid:DXImageTransform.Microsoft.gradient(startColorstr='#ff1ac6fc', endColorstr='#ff069bc7', GradientType=0);
                font-weight: 500;
            }

            #novethic_handler .page-articles-fiche .page-articles-fiche-headline-publication-date {
                display: inline-block;
                margin-bottom: 15px;
                margin-top: 0;
                font-size: 11px;
                line-height: 14px;
                font-family: Arial,"Helvetica Neue",Helvetica,sans-serif;
            }
        """)
