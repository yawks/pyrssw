from typing import Optional, cast
from utils.dom_utils import xpath
from handlers.feed_type.feed_arranger import FeedArranger
from lxml import etree
from lxml.builder import ElementMaker
from urllib.parse import quote_plus


NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/"
}


class AtomArranger(FeedArranger):

    def get_items(self, dom: etree) -> list:
        return dom.xpath(".//atom:entry", namespaces=NAMESPACES)

    def get_links(self, item) -> list:
        return item.xpath(".//atom:link", namespaces=NAMESPACES)

    def get_url_from_link(self, link: etree) -> str:
        return link.attrib["href"]

    def set_url_from_link(self, link: etree._Element, url: str):
        link.attrib["href"] = url
        link.text = url

    def get_descriptions(self, item) -> list:
        return item.xpath(".//atom:content", namespaces=NAMESPACES)

    def get_title(self, item: etree._Element) -> Optional[etree._Element]:
        title: Optional[etree._Elements] = None
        for t in xpath(item, ".//atom:title", namespaces=NAMESPACES):
            title = t
            break

        return title

    def get_img_url(self, node: etree) -> str:
        """get img url from enclosure or media:thumbnail tag if any

        Arguments:
            node {etree} -- item node of rss feed

        Returns:
            str -- the url of the image found in media:thumbnail tag
        """
        img_url = ""
        # media:thumbnail tag
        medias = node.xpath(
            ".//*[local-name()='thumbnail'][@url]", namespaces=NAMESPACES)
        if len(medias) > 0:
            img_url = medias[0].get('url')
        return img_url

    def replace_img_links(self, item: etree._Element, replace_with: str):
        for media in xpath(item, ".//*[local-name()='thumbnail']"):
            # media:thumbnail tag
            media.attrib["url"] = replace_with % quote_plus(
                cast(str, media.attrib["url"]))

    def set_thumbnail_item(self, item: etree._Element, img_url: str):
        medias = item.xpath(
            ".//*[local-name()='thumbnail'][@url]", namespaces=NAMESPACES)
        media: etree._Element
        if len(medias) > 0:
            media = medias[0]
        else:
            media = etree.Element("{%s}thumbnail" %
                                  NAMESPACES["media"], nsmap=NAMESPACES)
            item.append(media)

        media.attrib["url"] = img_url
