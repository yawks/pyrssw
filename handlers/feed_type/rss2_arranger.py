from handlers.feed_type.feed_arranger import FeedArranger
from lxml import etree


class RSS2Arranger(FeedArranger):
    """arrange feed by adding some pictures in description, ..."""

    def get_items(self, dom: etree) -> list:
        return dom.xpath("//item")

    def get_links(self, item: etree) -> list:
        return item.xpath(".//link")
    
    def get_url_from_link(self, link:etree) -> str:
        return link.text.strip()
    
    def set_url_from_link(self, link: etree, url: str):
        link.text = url

    def get_descriptions(self, item: etree) -> list:
        return item.xpath(".//description")

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
