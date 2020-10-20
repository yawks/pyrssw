from handlers.feed_type.feed_arranger import FeedArranger
from lxml import etree
from urllib.parse import quote_plus


NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}


class AtomArranger(FeedArranger):

    def get_items(self, dom: etree) -> list:
        return dom.xpath(".//atom:entry", namespaces=NAMESPACES)

    def get_links(self, item) -> list:
        return item.xpath(".//atom:link", namespaces=NAMESPACES)

    def get_url_from_link(self, link: etree) -> str:
        return link.attrib["href"]

    def set_url_from_link(self, link: etree, url: str):
        link.attrib["href"] = url
        link.text = url

    def get_descriptions(self, item) -> list:
        return item.xpath(".//atom:content", namespaces=NAMESPACES)

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
        for media in item.xpath(".//*[local-name()='thumbnail']"):
            # media:thumbnail tag
            media.attrib["url"] = replace_with % quote_plus(
                media.attrib["url"])
