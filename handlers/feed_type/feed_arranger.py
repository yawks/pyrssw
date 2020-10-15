from abc import ABCMeta, abstractmethod
import logging
from storage.article_store import ArticleStore
from typing import Dict, List, Optional
import datetime
import re
import html
from urllib.parse import urlparse, quote_plus, parse_qs
from lxml import etree


class FeedArranger(metaclass=ABCMeta):

    def __init__(self, module_name: str, serving_url_prefix: Optional[str], session_id: str) -> None:
        self.module_name: str = module_name
        self.serving_url_prefix: Optional[str] = serving_url_prefix
        self.session_id: str = session_id


    @abstractmethod
    def get_items(self, dom: etree) -> list:
        """Get items of the feed document (item or entry)

        Args:
            dom (etree): etree dom document

        Returns:
            list: items or entries
        """

    @abstractmethod
    def get_links(self, item: etree) -> list:
        """Get links from item depending on feed type (rss2, atom)

        Args:
            item (etree node object): etree node from a parsed feed

        Returns:
            list: list of links
        """

    @abstractmethod
    def get_descriptions(self, item: etree) -> list:
        """Get description items from item depending on feed type (rss2, atom)

        Args:
            item (etree node object): etree node from a parsed feed

        Returns:
            list: list of description items
        """

    @abstractmethod
    def get_img_url(self, node: etree) -> str:
        """Get image url depending on feed items which may contain some picture url

        Args:
            node (etree): Get image URL

        Returns:
            str: img url
        """
    
    @abstractmethod
    def get_url_from_link(self, link:etree) -> str:
        """Get url from etree link node

        Args:
            link (etree): etree node representing a link

        Returns:
            str: the url
        """
    
    @abstractmethod
    def set_url_from_link(self, link:etree, url: str):
        """Set the url for the etree link

        Args:
            link (etree): etree feed link item
            url (str): the url to set
        """

    def arrange(self, parameters: Dict[str, str], contents: str) -> str:
        result: str = contents

        try:
            result: str = contents
            if len(result.strip()) > 0:
                # I probably do not use etree as I should
                result = re.sub(
                    r'<\?xml [^>]*?>', '', result).strip()
                result = re.sub(
                    r'<\?xml-stylesheet [^>]*?>', '', result).strip()

                dom = etree.fromstring(result)

                # copy picture url from enclosure/thumbnail to a img tag in description (or add a generated one)
                for item in self.get_items(dom):
                    if self._arrange_feed_keep_item(item, parameters):
                        self._arrange_item(item, parameters)
                        self._arrange_feed_link(item, parameters)
                    else:
                        item.getparent().remove(item)

                result = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                    etree.tostring(dom, encoding='unicode')

        except etree.XMLSyntaxError as e:
            logging.getLogger().info(
                "[ %s ] - Unable to parse rss feed for module '%s' (%s), let's proceed anyway",
                datetime.datetime.now().strftime("%Y-%m-%d - %H:%M"),
                self.module_name,
                str(e))

        return result

    def _arrange_feed_keep_item(self, item: etree._Element, parameters: Dict[str, str]) -> bool:
        """return true if the item must not be deleted.
        The item must be deleted if the article has already been read.

        Arguments:
            item {etree._Element} -- rss feed item
            parameters {Dict[str, str]} -- url paramters which may contain the userid which is associated to read articles

        Returns:
            bool -- true if the item must not be deleted
        """
        feed_keep_item: bool = True
        if "userid" in parameters:
            for link in self.get_links(item):  # NOSONAR
                parsed = urlparse(link.text.strip())
                if "url" in parse_qs(parsed.query):
                    feed_keep_item = not ArticleStore.instance().has_article_been_read(
                        parameters["userid"], parse_qs(parsed.query)["url"][0])

        return feed_keep_item

    def _arrange_item(self, item: etree._Element, parameters: dict):
        descriptions = self.get_descriptions(item)

        if len(descriptions) > 0:
            if descriptions[0].text is not None and len(descriptions[0].xpath('.//img')) == 0 and etree.tostring(descriptions[0], encoding='unicode').find("&lt;img ") == -1:
                # if description does not have a picture, add one from enclosure or media:content tag if any
                img_url: str = self.get_img_url(item)

                if img_url == "":
                    # uses the ThumbnailHandler to fetch an image from google search images
                    img_url = "%s/thumbnails?request=%s" % (
                        self.serving_url_prefix, quote_plus(re.sub(r"</?description>", "", etree.tostring(descriptions[0], encoding='unicode')).strip()))

                img = etree.Element("img")
                img.set("src", img_url)
                descriptions[0].append(img)

            n = self._get_source(item)
            if n is not None:
                descriptions[0].append(n)

            """d escription_xml = etree.tostring(
                f, encoding='unicode')
            description_xml = re.sub(
                r'<description[^>]*>', "", description_xml)
            description_xml = description_xml.replace("</description>", "")
            """
            description_xml: str = descriptions[0].text
            for child in descriptions[0].getchildren():
                description_xml += etree.tostring(child, encoding='unicode')
            
            parent_obj = descriptions[0].getparent()
            parent_obj.remove(descriptions[0])

            description = etree.Element(descriptions[0].tag) #"description")
            description.text = html.unescape(
                description_xml.strip()).replace("&nbsp;", " ")
            parent_obj.append(description)
            

            if "debug" in parameters and parameters["debug"] == "true":
                p = etree.Element("p")
                i = etree.Element("i")
                i.text = "Session id: %s" % self.session_id
                p.append(i)
                descriptions[0].append(p)

    def _arrange_feed_link(self, item: etree._Element, parameters: Dict[str, str]):
        """arrange feed link, by adding dark and userid parameters if required

        Arguments:
            item {etree._Element} -- rss item
            parameters {Dict[str, str]} -- url parameters, one of them may be the dark boolean
        """
        suffix_url: str = ""
        for parameter in parameters:
            if parameter in ["dark", "debug", "userid", "plain"]:
                suffix_url += "&%s=%s" % (parameter, parameters[parameter])

        if suffix_url != "":
            for link in self.get_links(item):
                self.set_url_from_link(link, "%s%s" % (self.get_url_from_link(link).strip(), suffix_url))

    def _get_source(self, node: etree) -> Optional[etree._Element]:
        """get source url from link in 'url' parameter

        Arguments:
            node {etree} -- rss item node

        Returns:
            etree -- a node having the source url
        """
        n: etree = None
        links = self.get_links(node)
        if len(links) > 0:
            parsed = urlparse(self.get_url_from_link(links[0]))
            if "url" in parse_qs(parsed.query):
                a = etree.Element("a")
                a.set("href", parse_qs(parsed.query)["url"][0])
                a.text = "Source"
                n = etree.Element("p")
                n.append(a)
        return n
