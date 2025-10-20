from typing import Dict
from request.pyrssw_content import PyRSSWContent
import re

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import to_string


class LesJoiesDuCodeHandler(PyRSSWRequestHandler):
    """Handler for Les Joies du Code website.

    Most of the time the feed is enough to display the content of each entry.

    RSS parameters: None
    """

    def get_original_website(self) -> str:
        return "https://lesjoiesducode.fr/"

    def get_rss_url(self) -> str:
        return "http://lesjoiesducode.fr/atom"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://lesjoiesducode.fr/wp-content/uploads/2020/03/cropped-59760110_2118870124856761_2769282087964901376_n-32x32.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        r = session.get(url=self.get_rss_url(), headers={})

        # force encoding
        r.encoding = "utf-8"

        dom = etree.fromstring(r.text.encode("utf-8"))

        # Ensure media namespace is declared so the output uses the media: prefix
        media_ns = "http://search.yahoo.com/mrss/"
        # Ensure the media namespace is declared on the root element.
        # Creating or updating xmlns declarations via dom.attrib can lead to
        # incorrect bindings like 'ns0:media'. Instead, rebuild the root element
        # with an nsmap that includes the 'media' prefix merged with existing
        # namespaces.
        try:
            root = dom.getroottree().getroot()
        except Exception:
            root = dom

        # Merge existing nsmap (may be None) with the media prefix.
        existing_nsmap = getattr(root, 'nsmap', None) or {}
        # If media already present with the correct URI, skip rebuilding.
        if existing_nsmap.get('media') == media_ns:
            pass
        else:
            new_nsmap = dict(existing_nsmap)
            new_nsmap['media'] = media_ns

            # Build a new root element with the same tag, attrib, and children
            # but with the updated nsmap.
            new_root = etree.Element(root.tag, nsmap=new_nsmap)
            # copy attributes except xmlns declarations (they'll come from nsmap)
            for k, v in root.attrib.items():
                new_root.set(k, v)
            # move children
            for child in list(root):
                root.remove(child)
                new_root.append(child)

            # If dom is the root node itself, replace dom reference; otherwise
            # try to replace in-place by assigning into the tree.
            dom = new_root

        # Find entries and add a media:thumbnail element when a suitable media link is found
        entries = dom.xpath('//*[local-name()="entry"]')
        for entry in entries:
            thumb_url = None
            links = entry.xpath('./*[local-name()="link"]')
            for link in links:
                href = link.get("href")
                if href and re.search(
                    r"\.(webm|gif|mp4)(?:[?#].*)?$", href, re.IGNORECASE
                ):
                    thumb_url = href
                    break

            if thumb_url:
                thumb = etree.Element("{%s}thumbnail" % media_ns)
                thumb.set("url", thumb_url)
                entry.append(thumb)

        xml_str = etree.tostring(dom, encoding="utf-8").decode("utf-8")
        # Replace only hrefs that start with the site and have at least one
        # character after the trailing slash (i.e. not ending with "/").
        # Match the prefix and ensure the next character is not a double-quote.
        pattern = r'(href="https://lesjoiesducode.fr/)(?!\")'
        replacement = f'href="{self.url_prefix}?url=https://lesjoiesducode.fr/'
        xml_str = re.sub(pattern, replacement, xml_str)
        return xml_str

    def get_content(
        self, url: str, parameters: dict, session: requests.Session
    ) -> PyRSSWContent:
        page = session.get(url=url, headers={})
        content = self._clean_content(page.text)
        return PyRSSWContent(content)

    def _clean_content(self, c):
        content = ""
        if c is not None:
            dom = etree.HTML(c)
            objs = dom.xpath("//main/div/article/div")
            if len(objs) > 0:
                obj = objs[0]
                utils.dom_utils.delete_nodes(obj.xpath('//div[@class=""]'))
                content = to_string(obj)

        return content
