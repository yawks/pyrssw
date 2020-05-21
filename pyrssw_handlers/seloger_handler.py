import re

import requests
from lxml import etree

import utils.dom_utils
from handlers.launcher_handler import USER_AGENT
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class SeLogerHandler(PyRSSWRequestHandler):
    """Handler for SeLoger

    Handler name: seloger

    There is no rss feed provided, only a way to clean content when reading an URL.
    The provided page display only essential information of the asset and all the pictures.
    """

    @staticmethod
    def get_handler_name() -> str:
        return "seloger"

    def get_original_website(self) -> str:
        return "http://www.seloger.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict) -> str:
        return "<rss version=\"2.0\"/>"

    def get_content(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={"User-Agent": USER_AGENT})
        dom = etree.HTML(page.text)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "BookmarkButtonstyled")]',
            '//*[contains(@class, "TagsWithIcon")]',
            '//button',
            '//svg'
        ])

        content = utils.dom_utils.get_content(
            dom, ['//*[contains(@data-test, "summary")]',
                  "//*[contains(@class,\"ann_expiree g-vspace-400\")]"]) #expired article

        content += utils.dom_utils.get_content(
            dom, ['//*[@id="showcase-description"]'])

        content += "\n<div class=\"images\">\n"
        cpt = 1
        for div in dom.xpath("//div[@data-background]"):
            name = "Image #%d" % cpt
            content += "\t<br/><br/><img src=\"%s\" title=\"%s\" alt=\"%s\" />\n" % (
                div.attrib["data-background"], name, name)
            cpt = cpt + 1
        content += "</div>\n"

        return content
