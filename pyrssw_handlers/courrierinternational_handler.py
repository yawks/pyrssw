from typing import Dict
import re
import urllib.parse
import requests
from lxml import etree
from request.pyrssw_content import PyRSSWContent
from pyrssw_handlers.le_monde_handler import URL_CONNECTION, URL_DECONNECTION
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
import utils.dom_utils
from utils.dom_utils import to_string

URL_CONNECTION = "https://www.courrierinternational.com/login?destination=%3Cfront%3E"
URL_DECONNECTION = "https://www.courrierinternational.com/user/logout"


class CourrierInternationalHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.courrierinternational.fr">Courrier International</a> website.

    Handler name: courrierinternational

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.courrierinternational.com/"

    def get_rss_url(self) -> str:
        return "https://www.courrierinternational.com/feed/all/rss.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.courrierinternational.com/bucket/assets/0f89e5ddc5fb8557e5d8a3fa706d2f6ad55b5237/img/logos/favicon.ico"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r"<link>[^<]*</link>", "", feed)
        link = "<link>"
        feed = feed.replace('<guid isPermaLink="false">', link)
        feed = feed.replace('<guid isPermaLink="true">', link)
        feed = feed.replace("</guid>", "</link>")
        feed = feed.replace(
            link,
            "<link>%s?%surl="
            % (self.url_prefix, self._get_authentification_suffix(parameters)),
        )

        dom = etree.fromstring(feed.encode("utf-8"), parser=None)

        feed = to_string(dom)

        return feed

    def get_content(
        self, url: str, parameters: dict, session: requests.Session
    ) -> PyRSSWContent:
        self._authent(parameters, session)
        try:
            page = session.get(url=url)
            content = page.text.replace(">", ">\n")

            content = re.sub(r'src="data:image[^"]*', "", content)
            content = content.replace("data-src", "style='height:100%;width:100%' src")
            dom = etree.HTML(content, parser=None)

            utils.dom_utils.delete_xpaths(
                dom,
                [
                    '//div[contains(@class, "article-metas")]',
                    '//div[contains(@class,"article-secondary")]',
                    '//aside[contains(@class,"article-tools")]',
                    '//aside[contains(@class,"item")]',
                    '//*[contains(@class,"asset-encadre")]',
                    '//*[contains(@class,"stories-paywall")]',
                    '//*[contains(@class,"asset-read-more")]'
                ],
            )

            header = utils.dom_utils.get_content(
                dom, ['//header[@class="article-header"]']
            )

            body = utils.dom_utils.get_content(dom, [
                '//div[@class="article-content"]',
                '//article[contains(@class,"card")]'
                ])

            content = header + body

            if len(content.replace("\n", "").strip()) < 150:
                # less than 150 chars, we did not manage to get the content, use readability facility
                content = super().get_readable_content(session, url)
        finally:
            self._unauthent(session)

        return PyRSSWContent(
            content,
            """
            #courrierinternational_handler h1 {display:inline}
            #courrierinternational_handler span.strapline {font-weight: 500;}
            #courrierinternational_handler .article-heading span.strapline {font-size: 170%;color: #ff7d24;}
            #courrierinternational_handler .article-header ul {list-style:none;padding:0;margin:0}
            #courrierinternational_handler li {display: inline-block;text-transform: uppercase;font-size: 14px;letter-spacing: 2px;}
            #courrierinternational_handler .article-header .item:not(:last-child):after {content: "\\A0\\2022\\A0";font-weight: 600;}
        """,
        )

    def _authent(self, parameters: dict, session: requests.Session):
        page = session.get(url=URL_CONNECTION)
        if "login" in parameters and "password" in parameters:
            idx = page.text.find('name="form_build_id" value="')
            if idx > -1:
                start = page.text[idx + len('name="form_build_id" value="') :]
                token = start[0 : start.find('"')]

                data = {
                    "name": parameters["login"],
                    "pass": parameters["password"],
                    "form_build_id": token,
                    "form_id": "user_login_block",
                    "ci_promo_code_code": "",
                    "op": "Se connecter",
                }
                session.post(url=URL_CONNECTION, data=data, headers={})

    def _get_authentification_suffix(self, parameters: dict):
        suffix = ""
        if "login" in parameters and "password" in parameters:
            suffix = "login=%s&amp;password=%s&amp;" % (
                urllib.parse.quote_plus(parameters["login_crypted"]),
                urllib.parse.quote_plus(parameters["password_crypted"]),
            )

        return suffix

    def _unauthent(self, session: requests.Session):
        session.get(url=URL_DECONNECTION, headers={})
