from typing import Dict, List, Optional, cast
from utils.dom_utils import xpath
from handlers.feed_type.feed_arranger import FeedArranger
from lxml import etree
from urllib.parse import quote_plus


class RSS2Arranger(FeedArranger):
    """arrange feed by adding some pictures in description, ..."""

    def get_items(self, dom: etree) -> list:
        return dom.xpath("//item")

    def get_links(self, item: etree) -> list:
        return item.xpath(".//link")

    def get_url_from_link(self, link: etree) -> str:
        return "" if link.text is None else link.text.strip()

    def set_url_from_link(self, link: etree._Element, url: str):
        link.text = url

    def get_descriptions(self, item: etree) -> list:
        return item.xpath(".//description")

    def get_title(self, item: etree._Element) -> Optional[etree._Element]:
        title: Optional[etree._Elements] = None
        for t in cast(List[etree._Element], item.xpath(".//title")):
            title = t
            break

        return title

    def get_img_url(self, node: etree) -> str:
        """get img url from enclosure or media:content tag if any

        Arguments:
            node {etree} -- item node of rss feed

        Returns:
            str -- the url of the image found in enclosure or media:content tag
        """
        img_url = ""
        enclosures = node.xpath(".//enclosure")
        # media:content tag
        medias = node.xpath(".//*[local-name()='content'][@url]")
        if len(enclosures) > 0:
            img_url = enclosures[0].get('url')
        elif len(medias) > 0:
            img_url = medias[0].get('url')
        return img_url

    def replace_img_links(self, item: etree._Element, replace_with: str):
        for enclosure in cast(List[etree._Element], item.xpath(".//enclosure")):
            # media:content tag
            enclosure.attrib["url"] = replace_with % enclosure.attrib["url"]

        for media in cast(List[etree._Element], item.xpath(".//*[local-name()='content'][@url]")):
            media.attrib["url"] = replace_with % quote_plus(
                cast(str, media.attrib["url"]))

    def set_thumbnail_item(self, item: etree._Element, img_url: str):
        enclosures = item.xpath(".//enclosure")
        enclosure: etree._Element
        if len(enclosures) > 0:
            enclosure = enclosures[0]
        else:
            enclosure = etree.Element("enclosure")
            item.append(enclosure)

        enclosure.attrib["url"] = img_url
        enclosure.attrib["type"] = "image/jpeg"

    def arrange_feed_top_level_element(self, dom: etree._Element, rss_url_prefix: str, parameters: Dict[str, str], favicon_url: str):
        # update or create icon tag element in channel
        urls = xpath(dom, "./channel/image/url")
        url_node: etree._Element
        if len(urls) == 0:
            image_node: etree._Element = etree.Element("image")
            url_node = etree.Element("url")
            image_node.append(url_node)
            xpath(dom, "./channel")[0].insert(0, image_node)
        else:
            url_node = urls[0]
        url_node.text = favicon_url

        # arrange links in channel
        other_link_nodes = xpath(
            dom, "./channel/*[local-name()='link' and @href] | ./channel/link")
        for link_node in other_link_nodes:
            if "href" in link_node.attrib:
                link_node.attrib["href"] = self._generated_complete_url(
                    rss_url_prefix, parameters)
            else:
                link_node.text = self._generated_complete_url(
                    rss_url_prefix, parameters)
