from typing import Dict, cast
from request.pyrssw_content import PyRSSWContent
import re
import urllib.parse
from utils.url_utils import is_url_valid

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import get_content, to_string, xpath

FILTERS = {
    "A la Une": "alaune",
    "Politique": "politique",
    "Société": "societe",
    "Monde": "monde",
    "Science et santé": "science-et-sante",
    "Culture": "culture",
    "Sport": "sport",
    "Education": "education",
    "Emploi": "emploi",
    "Styles": "styles",
    "Tendances": "tendances",
    "Insolite": "insolite",
    "Médias": "medias",
    "Vie Pratique": "viepratique",
    "Régions": "regions",
    "Enquete": "enquete",
    "Vidéo": "videos",
    "Nos dossiers": "dossiers"
}


class LExpress(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.lexpress.fr">L'Express'</a> website.

    Handler name: lexpress

    RSS parameters:
     - filter : A la Une, Politique, Société, Monde, Science et santé, Culture, Sport, Education, Emploi, Styles, Tendances, Insolite, Médias, Vie Pratique, Régions, Enquete, Vidéo, Nos dossiers
       eg :
         - /lexpress/rss?filter=Politique

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.lexpress.fr/"

    def get_rss_url(self) -> str:
        return "https://www.lexpress.fr/rss/%s.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.lexpress.fr/Favicone.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url() %
                           FILTERS.get(parameters.get("filter", "A la Une"), "alaune"), headers={}).text

        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        link = '<link>'
        feed = feed.replace('<guid isPermaLink="false">', link)
        feed = feed.replace('<guid isPermaLink="true">', link)
        feed = feed.replace('</guid>', '</link>')
        # f eed = feed.replace(link, '<link>%ssurl=' % (
        #    self.url_prefix))

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)
        for node in xpath(dom, "//link|//guid"):
            node.text = "%s" % self.get_handler_url_with_parameters(
                {"url": cast(str, node.text)})
        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:

        page = session.get(url=url)
        content = page.text

        dom = etree.HTML(content)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "meta__social")]',
            '//*[contains(@class,"header--content")]',
            '//*[contains(@class,"article__subhead")]',
            '//*[contains(@class,"block_pub")]',
            '//*[contains(@class,"search__container")]',
            '//*[contains(@class,"article__metas")]',
            '//*[contains(@class,"abo-inread")]',
            '//*[contains(@class,"sgt-inread")]',
            '//*[@id="placeholder--plus-lus"]',
            '//*[@id="placeholder--opinion"]',
            '//*[contains(@class,"article__popin")]',
            '//*[contains(@class,"nav_footer")]',
            '//*[contains(@class,"bloc_surfooter")]',
            '//*[contains(@class,"js-outbrain")]',
            '//*[contains(@class,"article__breadcrumb")]',
            '//*[contains(@class,"article__nav-seo")]',
            '//*[contains(@class,"article__footer")]',
            '//*[contains(@class,"article__item--rebond")]',
            '//*[@id="footer"]'
        ])

        content = get_content(dom, [
            '//div[contains(@class,"article")]'
        ])

        return PyRSSWContent(content, """
.article__illustration img {
    width: 100%!important;
}
        """)
