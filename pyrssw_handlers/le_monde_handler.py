from typing import Dict, List
from request.pyrssw_content import PyRSSWContent
import re
import urllib.parse
from utils.url_utils import is_url_valid

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath

URL_CONNECTION = "https://secure.lemonde.fr/sfuser/connexion"
URL_DECONNECTION = "https://secure.lemonde.fr/sfuser/deconnexion"

STREAMS = {
    "a_la_une": "https://www.lemonde.fr/rss/une.xml",
    "en_continu": "https://www.lemonde.fr/rss/en_continu.xml",
    "videos": "https://www.lemonde.fr/videos/rss_full.xml",
    "portfolios": "https://www.lemonde.fr/photo/rss_full.xml",
    "les_plus_lus": "https://www.lemonde.fr/rss/plus-lus.xml",
    "les_plus_partages": "https://www.lemonde.fr/rss/plus-partages.xml",
    "politique": "https://www.lemonde.fr/politique/rss_full.xml",
    "societe": "https://www.lemonde.fr/societe/rss_full.xml",
    "les_decodeurs": "https://www.lemonde.fr/les-decodeurs/rss_full.xml",
    "justice": "https://www.lemonde.fr/justice/rss_full.xml",
    "police": "https://www.lemonde.fr/police/rss_full.xml",
    "campus": "https://www.lemonde.fr/campus/rss_full.xml",
    "education": "https://www.lemonde.fr/education/rss_full.xml",
    "a_la_une_international": "https://www.lemonde.fr/international/rss_full.xml",
    "a_la_une_economie": "https://www.lemonde.fr/economie/rss_full.xml",
    "a_la_une_sport": "https://www.lemonde.fr/sport/rss_full.xml",
    "a_la_une_planete": "https://www.lemonde.fr/planete/rss_full.xml",
    "a_la_une_sciences": "https://www.lemonde.fr/sciences/rss_full.xml",
    "a_la_une_idees": "https://www.lemonde.fr/idees/rss_full.xml",
    "a_la_une_m_le_mag": "https://www.lemonde.fr/m-le-mag/rss_full.xml",
}


class LeMondeHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.lemonde.fr">Le Monde</a> website.

    Handler name: lemonde

    RSS parameters:
     - filter : a_la_une, en_continu, videos, portfolios, les_plus_lus, les_plus_partages, politique, societe, les_decodeurs, justice, police, campus, education, la_une_international, la_une_economie, la_une_sport, la_une_planete, la_une_sciences, la_une_idees, la_une_m_le_mag
       eg :
         - /lemonde/rss?filter=politique            #only feeds about politique
         - /lemonde/rss?filter=politique,societe    #only feeds about politique and societe
     - login : if you have an account you can use it to fetch full articles available only for subscribers
     - password : password of your account

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.lemonde.fr/"

    def get_rss_url(self) -> str:
        return "https://www.lemonde.fr/rss/une.xml"

    @staticmethod
    def get_favicon_url(_: Dict[str, str]) -> str:
        return "https://www.lemonde.fr/dist/assets/img/logos/favicon.ico"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed_urls: List[str] = self._get_feed_urls(parameters)

        feed = ""
        dom = None
        for feed_url in feed_urls:
            # consolidate streams in only one removing duplicates
            feed = session.get(url=feed_url, headers={}).text
            feed = re.sub(r"<link>[^<]*</link>", "", feed)
            link = "<link>"
            feed = feed.replace('<guid isPermaLink="false">', link)
            feed = feed.replace('<guid isPermaLink="true">', link)
            feed = feed.replace("</guid>", "</link>")
            if dom is None:
                dom = etree.fromstring(feed.encode("utf-8"), parser=None)
            else:
                channel = xpath(dom, "//channel")[0]
                dom2 = etree.fromstring(feed.encode("utf-8"), parser=None)
                for link in xpath(dom2, "//link"):
                    if len(xpath(dom, '//link[text()="' + link.text + '"]')) == 0:
                        channel.append(link.getparent())

        if dom is not None:
            feed = to_string(dom)
            feed = feed.replace(
                "<link>",
                "<link>%s?%surl="
                % (self.url_prefix, self._get_authentification_suffix(parameters)),
            )

        return feed

    def _get_feed_urls(self, parameters: dict) -> List[str]:
        feed_urls: List[str] = []
        if "filter" in parameters:
            for feed_name in parameters["filter"].split(","):
                if feed_name.strip() in STREAMS:
                    feed_urls.append(STREAMS[feed_name.strip()])

        if len(feed_urls) == 0:
            feed_urls.append(self.get_rss_url())  # default stream

        return feed_urls

    def _get_authentification_suffix(self, parameters: dict):
        suffix = ""
        if "login" in parameters and "password" in parameters:
            suffix = "login=%s&amp;password=%s&amp;" % (
                urllib.parse.quote_plus(parameters["login_crypted"]),
                urllib.parse.quote_plus(parameters["password_crypted"]),
            )

        return suffix

    def get_content(
        self, url: str, parameters: dict, session: requests.Session
    ) -> PyRSSWContent:
        self._authent(parameters, session)
        try:
            page = session.get(url=url)
            content = page.text

            dom = etree.HTML(content, parser=None)

            utils.dom_utils.delete_xpaths(
                dom,
                [
                    '//*[contains(@class, "meta__social")]',
                    '//*[contains(@class, "breadcrumb")]',
                    '//*[contains(@class, "article__reactions")]',
                    '//*[contains(@class, "services")]',
                    '//*[contains(@class, "article__footer-single")]',
                    '//*[contains(@class, "wp-socializer")]',
                    '//*[contains(@class, "insert")]',
                    '//*[@id="comments"]',  # blog
                    '//*[contains(@class, "post-navigation")]',  # blog
                    '//*[contains(@class, "entry-footer")]',  # blog
                    '//*[contains(@class, "catcher")]',  # tribune
                    "//aside",
                    '//*[@id="d_overlay"]',
                ],
            )

            self.process_pictures(dom)
            self.process_inread(dom)

            # le monde rss provides many sub websites with different html architecture
            content = utils.dom_utils.get_content(
                dom,
                [
                    '//*[contains(@class, "zone--article")]',
                    '//*[contains(@class, "article--content")]',  # tribune
                    '//*[@id="post-container"]',
                    '//*[@id="main"]',  # blog
                ],
            )

        finally:
            self._unauthent(session)
        return PyRSSWContent(content)

    def process_inread(self, dom):
        for inread in dom.xpath('//*[@data-format="inread"]'):
            for child in inread:
                inread.getparent().append(child)
            inread.getparent().remove(inread)

    def process_pictures(self, dom):
        for img in xpath(dom, "//img[@data-srcset]"):
            elements = img.attrib["data-srcset"].split(" ")
            for element in elements:
                if is_url_valid(element):
                    img.attrib["src"] = element
                    break

    def _authent(self, parameters: dict, session: requests.Session):
        page = session.get(url=URL_CONNECTION)
        if "login" in parameters and "password" in parameters:
            dom = etree.HTML(page.text, parser=None)
            input_node_key = None
            for input in xpath(dom, '//input[@type="hidden"]'):
                if (
                    input.attrib.get("id", "") not in ["newsletters", "article"]
                    and len(input.attrib.get("id", "")) > 10
                ):
                    input_node_key = input
                    break
            if input_node_key is not None:
                data = {
                    "email": parameters["login"],
                    "password": parameters["password"],
                    "newsletters": "[]",
                    "article": "",
                    input_node_key.attrib["id"]: input_node_key.attrib.get("value", ""),
                }
                session.post(
                    url=URL_CONNECTION,
                    data=data,
                    headers=self._get_headers(URL_CONNECTION),
                )

    def _get_headers(self, referer):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://secure.lemonde.fr/",
            "Host": "secure.lemonde.fr",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": referer,
        }

    def _unauthent(self, session: requests.Session):
        session.get(url=URL_DECONNECTION, headers=self._get_headers("/"))
        # session.close()
