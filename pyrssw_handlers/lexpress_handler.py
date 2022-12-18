import json
from typing import Dict, cast
from handlers.launcher_handler import USER_AGENT
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

    def get_handler_name(self, parameters: Dict[str, str]):
        suffix = " - " + \
            parameters["filter"] if parameters.get("filter", "") != "" else ""
        return "L'Express" + suffix

    def get_original_website(self) -> str:
        return "https://www.lexpress.fr/"

    def get_rss_url(self) -> str:
        return "https://www.lexpress.fr/rss/%s.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.lexpress.fr/pf/resources/Favicon_152x152.png?d=574"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url() %
                           FILTERS.get(parameters.get("filter", "A la Une"), "alaune"), headers={}).text

        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        link = '<link>'
        feed = feed.replace('<guid isPermaLink="false">', link)
        feed = feed.replace('<guid isPermaLink="true">', link)
        feed = feed.replace('</guid>', '</link>')

        dom = etree.fromstring(feed.encode("utf-8"))
        for node in xpath(dom, "//link|//guid"):
            node.text = "%s" % self.get_handler_url_with_parameters(
                {"url": cast(str, node.text), "filter": parameters.get("filter", "")})
        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:

        page = session.get(url=url, headers={"User-Agent": USER_AGENT})
        content = page.text

        dom = etree.HTML(content)

        paywall_content = _process_paywall_json(content, dom)
        if paywall_content == "":
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
                '//*[contains(@class,"groupement__nav-seo")]',
                '//*[contains(@class,"groupement__breadcrumb")]',
                '//*[contains(@class,"groupement__subhead")]',
                '//*[@id="footer"]'
            ])

            _process_imgs(dom)

            content = get_content(dom, [
                '//div[contains(@class,"article")]',
                '//div[contains(@class,"groupement")]'
            ])
        else:
            content = paywall_content

        return PyRSSWContent(content, """
.article__illustration img {
    width: 100%!important;
}

h2 a {
    line-height: 1.1;
    text-decoration: none;
}

span.thumbnail__date.text--info {
    font-style: italic;
    margin-bottom: 15px;
    font-size: 12px;
}
        """)


def _process_paywall_json(content: str, dom: etree._Element) -> str:
    found_content: str = ""
    FUSION_MARKER = "Fusion.globalContent="
    start_idx = content.find(FUSION_MARKER)
    if start_idx > -1:
        end_idx = content[start_idx+len(FUSION_MARKER):].find("};Fusion")
        json_str = content[start_idx +
                           len(FUSION_MARKER):start_idx+len(FUSION_MARKER)+end_idx+1]
        json_content = json.loads(json_str)

        found_content = "<h1>%s</h1>" % json_content.get(
            "headlines", {}).get("basic", "")

        elements = json_content.get("content_elements", [])

        for element in elements:
            found_content += _process_paywall_element(element)

        if json_content.get("promo_items", {}).get("youtube", "") != "":
            found_content += json_content["promo_items"]["youtube"].get("embed", {}).get("config", {}).get("html", "")
    
    else:
        # this is working, but we miss pictures + paragraph formatting.
        for script in xpath(dom, "//script"):
            if script.attrib.get("type", "") == "application/ld+json" and script.text[0:1] == "{":
                json_content = json.loads(script.text)
                if json_content.get("@type", "") == "NewsArticle" and "articlebody" in json_content:
                    found_content = json_content.get("articlebody")
                    break

    return found_content


def _process_paywall_element(element: dict) -> str:
    found_content: str = ""

    if element["type"] == "text":
        found_content += "<p>%s</p>\n" % element.get("content")
    elif element["type"] == "image":
        found_content += "<img src=\"%s\">\n" % element.get("url")
    elif element["type"] == "header":
        found_content += "<h%d>%s</h%d>\n" % (int(element.get(
            "level", 1)) + 1, element.get("content", ""), int(element.get("level", 1)) + 1)
    elif element["type"] == "list":
        list_tag_name = "ul"
        if element["list_type"] != "unordered":
            list_tag_name = "ol"

        found_content += f"<{list_tag_name}>"
        for item in element["items"]:
            found_content += "<li>%s</li>\n" % _process_paywall_element(item)
        found_content += f"</{list_tag_name}>"

    elif element["type"] == "quote":
        for item in element["content_elements"]:
            found_content += "<blockquote>%s</blockquote>\n" % _process_paywall_element(
                item)

    elif element["type"] == "oembed_response":
        html = element.get("raw_oembed", {}).get("html", "")
        found_content += html
        if html == "":
            found_content += "<i>Unhandled subtype '%s' type '%s'</i>\n" % (element["subtype"], element["type"])

    elif element["type"] == "link_list":
        for item in element.get("items", []):
            if item.get("type", "") == "interstitial_link":
                found_content += "<p><a href=\"%s\">%s</a></p>\n" % (
                    item.get("url"), item.get("content"))
            else:
                found_content += "<p><i>Unhandled link_list type '%s'</i></p>\n" % item.get(
                    "type", "")

    else:
        found_content += "<p><i>unhandled type '%s'</i></p>\n" % element.get(
            "type")

    return found_content


def _process_imgs(dom: etree._Element):
    for img in xpath(dom, "//img[@data-srcset]"):
        img.attrib["src"] = img.attrib["data-srcset"].strip().split(" ")[0]
        del img.attrib["data-srcset"]
        if "data-src" in img.attrib:
            del img.attrib["data-src"]
