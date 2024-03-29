import re
from typing import Dict, cast
from request.pyrssw_content import PyRSSWContent
import requests
from lxml import etree
from utils.dom_utils import to_string, xpath
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class FuturaSciencesHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.futura-sciences.com">Futura Sciences</a> website.

    Handler name: futurasciences

    RSS parameters:
     - filters :

       to invert filtering, prefix it with: ^
       eg :
         - /futurasciences/rss?filter=Etoiles              #only feeds about Etoiles
         - /futurasciences/rss?filter=Volcan,Etoiles       #only feeds about Volcan and Etoiles
         - /futurasciences/rss?filter=^Volcan,Etoiles      #all feeds but Volcan and Etoiles

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.futura-sciences.com/"

    def get_rss_url(self) -> str:
        return "https://www.futura-sciences.com/rss/actualites.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.futura-sciences.com/favicon-32x32.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url()).text

        dom = etree.fromstring(feed.encode("utf-8"))

        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        # replace video links, they must be processed by getContent
        for node in xpath(dom, "//link|//guid"):
            node.text = "%s" % self.get_handler_url_with_parameters(
                {"url": cast(str, node.text)})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url)
        content = page.text.replace(">", ">\n")

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace(
            "data-src", "style='height:100%;width:100%' src")
        content = content.replace('data-fs-media', '')
        content = content.replace('class="fs-media"', '')
        dom = etree.HTML(content)

        # rework images
        imgs = dom.xpath('//img[contains(@class, "img-responsive")]')
        for img in imgs:
            new_img = etree.Element("img")
            new_img.set("src", img.attrib["src"])
            img.getparent().getparent().getparent().getparent().getparent().append(new_img)

        title = utils.dom_utils.get_content(dom, ["//h1"])
        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "module-toretain")]',
            '//*[contains(@class,"hubbottom2")]',
            '//*[contains(@class, "image-module")]/img',
            '//*[contains(@class, "social-button")]',
            '//section[contains(@class, "breadcrumb")]',
            '//section[contains(@class, "author-box")]',
            '//section[contains(@class, "connexelinks")]',
            '//section[contains(@class, "sidebar-module")]',
            '//*[contains(@class, "ICON-QUICKREAD")]/parent::*/parent::*'
        ])

        _process_futura_video(dom)

        content, _ = utils.dom_utils.get_all_contents(
            dom, [
                '//section[contains(@class,"article-hero")]',
                '//div[contains(@class,"video-top")]',
                '//div[contains(@class,"article-column")]'
            ])
        if title not in content:
            content = title + content

        return PyRSSWContent(content)


def _process_futura_video(dom: etree._Element):
    # replace div with class vsly-player to iframe with url using data-iframe tag attribute value
    for vid in xpath(dom, '//*[contains(@class,"vsly-player")]'):
        if vid.attrib.get("data-iframe", "") != "":
            vid.tag = "iframe"
            vid.attrib["style"] = ""
            vid.attrib["src"] = vid.attrib.get("data-iframe")
            
