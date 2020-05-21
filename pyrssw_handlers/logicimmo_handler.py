import re

import requests
from lxml import etree

import utils.dom_utils
from handlers.launcher_handler import USER_AGENT
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class LogicImmoHandler(PyRSSWRequestHandler):
    """Handler for LogicImmo

    Handler name: logicimmo

    There is no rss feed provided, only a way to clean content when reading an URL.
    The provided page display only essential information of the asset and all the pictures.
    """

    @staticmethod
    def get_handler_name() -> str:
        return "logicimmo"

    def get_original_website(self) -> str:
        return "http://www.logic-immo.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict) -> str:
        return "<rss version=\"2.0\"/>"

    def get_content(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={"User-Agent": USER_AGENT})
        dom = etree.HTML(page.text)

        imgs = "\n<div class=\"images\">\n"
        cpt = 1
        for img in dom.xpath("//img[contains(@src,'182x136')]"):
            imgs += "<img src=\"%s\" alt=\"Image #%d\" title=\"Image #%d\" />" % (
                img.attrib["src"].replace("182x136", "800x600"), cpt, cpt)
            cpt = cpt + 1

        imgs += "\n</div>\n"

        
        #utisls.dom_utils.delete_xpaths(dom, [
            #'//*[contains(@class, "icon-camera")]',
            #'//*[contains(@class, "monthPricing")]',
            #'//*[contains(@class, "toggleThumbs")]',
            #'//*[contains(@class, "offer-carousel")]',
            #'//*[contains(@class, "icon-print")]',
            #'//button'
        #])
        

        content = utils.dom_utils.get_content(
            dom, ['//*[contains(@class, "offer-block")]']).replace("182x136", "800x600")

        content += utils.dom_utils.get_content(
            dom, ['//*[contains(@class, "offer-description")]'])

        return """
    <div class=\"main-content\">
        %s
        %s
    </div>""" % (content, imgs)
