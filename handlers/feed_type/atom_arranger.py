from datetime import datetime, timezone
import timeago
import maya
from typing import Dict, List, Optional, Tuple, cast
from utils.dom_utils import get_first_node, xpath
from handlers.feed_type.feed_arranger import FeedArranger
from lxml import etree
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

    def get_img_url(self, node: etree._Element) -> str:
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

    def arrange_feed_top_level_element(self, dom: etree._Element, rss_url_prefix: str, parameters: Dict[str, str], favicon_url:str):
        icons = xpath(dom, "./icon")
        icon_node: etree._Element
        if len(icons) == 0:
            icon_node = etree.Element("icon")
            dom.insert(0, icon_node)
        else:
            icon_node = icons[0]
        icon_node.text = favicon_url
        icon = etree.Element("{%s}icon" %
                                  NAMESPACES["atom"], nsmap=NAMESPACES)
        icon.text = favicon_url
        dom.insert(0, icon)

        # arrange links in channel
        other_link_nodes = xpath(
            dom, "./*[local-name()='link' and @type='application/atom+xml']")
        for link_node in other_link_nodes:
            if "href" in link_node.attrib:
                link_node.attrib["href"] = self._generated_complete_url(
                    rss_url_prefix, parameters)
            else:
                link_node.text = self._generated_complete_url(
                    rss_url_prefix, parameters)

    def get_items_tuples(self, dom: etree._Element) -> List[Tuple[str, str, str, str]]:
        items_tuples = []
        for entry in xpath(dom, "//atom:entry", NAMESPACES):
            url = ""
            if len(self.get_links(entry)) > 0:
                url = cast(str, self.get_links(entry)[0].attrib.get("href"))

            img_url = self.get_img_url(entry)
            title = "" if self.get_title(entry) is None else cast(etree._Element, self.get_title(entry)).text

            pub_date = ""
            pub_date_node = get_first_node(entry, [".//atom:published"], NAMESPACES)
            if pub_date_node is not None:  # improve that finding local timezone name
                pub_date = timeago.format(maya.parse(cast(str, pub_date_node.text)).datetime(
                    to_timezone="Europe/Paris"), datetime.now(timezone.utc))

            items_tuples.append((url, img_url, title, pub_date))
        
        return items_tuples