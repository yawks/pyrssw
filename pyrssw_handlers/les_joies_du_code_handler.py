from typing import Dict, Optional
from request.pyrssw_content import PyRSSWContent
import re

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath


class LesJoiesDuCodeHandler(PyRSSWRequestHandler):
    """Handler for Les Joies du Code website.

    Most of the time the feed is enough to display the content of each entry.

    RSS parameters: None
    """

    def get_original_website(self) -> str:
        return "https://lesjoiesducode.fr/"

    def get_rss_url(self) -> str:
        return "http://lesjoiesducode.fr/rss"
    
    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://lesjoiesducode.fr/wp-content/uploads/2020/03/cropped-59760110_2118870124856761_2769282087964901376_n-32x32.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        r = session.get(url=self.get_rss_url(), headers={})

        # force encoding
        r.encoding = "utf-8"
        feed = r.text.replace("<link>", "<link>%s?url=" % self.url_prefix)
        feed = re.sub(
            r'<guid isPermaLink="false">https://lesjoiesducode.fr/\?p=[^<]*</guid>', r"", feed)

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()

        dom = etree.fromstring(feed)
        for item in xpath(dom, "//item"):
            for child in item.getchildren():  # did not find how to xpath content:encoded tag
                if child.tag.endswith("encoded"):
                    c = self._clean_content(
                        '<div class="blog-post">' + child.text + '</div>')
                    child.text = c  # "<![CDATA[" + c + "]]>"

        return to_string(dom)

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url, headers={})
        content = self._clean_content(page.text)
        return PyRSSWContent(content)

    def _clean_content(self, c):
        content = ""
        if c is not None:
            dom = etree.HTML(c)
            utils.dom_utils.delete_xpaths(dom, [
                '//*[@class="permalink-pagination"]',
                '//*[@class="social-share"]',
                '//*[@class="post-author"]'
            ])

            objs = dom.xpath('//object')
            for obj in objs:
                if obj.attrib["data"].lower().endswith(".gif"):
                    src = obj.attrib["data"]
                    img = etree.Element("img")
                    img.set("src", src)
                    obj.getparent().getparent().getparent().getparent().append(img)

            video_content = utils.dom_utils.get_content(
                dom, ['//*[contains(@class,"blog-post-content")]//video'])

            utils.dom_utils.delete_nodes(dom.xpath('//video'))
            content = utils.dom_utils.get_content(
                dom, ['//div[contains(@class, "blog-post")]', '//div[contains(@class,"blog-post-content")]'])

            if len(content) < 50:
                # means there is no gif
                content = video_content
            else:
                content = content.replace('<div class="blog-post">', '')
                content = content.replace(
                    '<div class="blog-post-content">', '')
                content = content.replace('</div>', '')
                content = re.sub(r'src="data:image[^"]*', '', content)
                content = content.replace(
                    "data-src", "style='height:100%;width:100%' src")
                content = re.sub(r'<!--(.*)-->', r"", content, flags=re.S)
        return content
