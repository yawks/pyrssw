from abc import ABCMeta, abstractmethod
import logging
from utils.dom_utils import to_string, translate_dom, xpath
from storage.article_store import ArticleStore
from typing import Dict, Optional, cast
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
    def get_items(self, dom: etree._Element) -> list:
        """Get items of the feed document (item or entry)

        Args:
            dom (etree): etree dom document

        Returns:
            list: items or entries
        """

    @abstractmethod
    def get_links(self, item: etree._Element) -> list:
        """Get links from item depending on feed type (rss2, atom)

        Args:
            item (etree node object): etree node from a parsed feed

        Returns:
            list: list of links
        """

    @abstractmethod
    def get_descriptions(self, item: etree._Element) -> list:
        """Get description items from item depending on feed type (rss2, atom)

        Args:
            item (etree node object): etree node from a parsed feed

        Returns:
            list: list of description items
        """

    @abstractmethod
    def get_title(self, item: etree._Element) -> Optional[etree._Element]:
        """Get title of the item feed entry

        Args:
            item ([type]): item etree Element

        Returns:
            Optional[etree._Elements]: title etree Element
        """

    @abstractmethod
    def get_img_url(self, node: etree._Element) -> str:
        """Get image url depending on feed items which may contain some picture url

        Args:
            node (etree): Get image URL

        Returns:
            str: img url
        """

    @abstractmethod
    def get_url_from_link(self, link: etree._Element) -> str:
        """Get url from etree link node

        Args:
            link (etree): etree node representing a link

        Returns:
            str: the url
        """

    @abstractmethod
    def set_url_from_link(self, link: etree._Element, url: str):
        """Set the url for the etree link

        Args:
            link (etree): etree feed link item
            url (str): the url to set
        """

    @abstractmethod
    def replace_img_links(self, item: etree._Element, replace_with: str):
        """Replace img links with given string mask

        Args:
            item (etree._Element): etree Element
            replace_with (str): string to use to replace the img links: if this string contains "%s" it will be used to set the original img link: ie "/thumbnail?url=%s"
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

                for item in self.get_items(dom):
                    if self._arrange_feed_keep_item(item, parameters):
                        self._arrange_item(item, parameters)
                        self._arrange_feed_link(item, parameters)
                    else:
                        item.getparent().remove(item)

                result = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                    to_string(dom)

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
            for link in self.get_links(item):
                if link.text is not None:
                    parsed = urlparse(link.text.strip())
                elif "href" in link.attrib:
                    parsed = urlparse(link.attrib["href"].strip())
                else:
                    logging.getLogger().info("Unable to find URL in item : (%s)" %
                                             to_string(item))
                    continue
                if "url" in parse_qs(parsed.query):
                    feed_keep_item = not ArticleStore.instance().has_article_been_read(
                        parameters["userid"], parse_qs(parsed.query)["url"][0])

        return feed_keep_item

    def _arrange_item(self, item: etree._Element, parameters: dict):
        descriptions = self.get_descriptions(item)

        if len(descriptions) > 0:
            description: etree._Element = descriptions[0]
            self._arrange_description_image(item, description, parameters)

            n = self._get_source(item)
            if n is not None:
                description.append(n)

            description_xml: str = ""
            if descriptions[0].text is not None:
                description_xml = descriptions[0].text
            for child in descriptions[0].getchildren():
                description_xml += to_string(child)

            parent_obj = descriptions[0].getparent()
            parent_obj.remove(descriptions[0])

            description = etree.Element(descriptions[0].tag)  # "description")
            description.text = html.unescape(
                description_xml.strip()).replace("&nbsp;", " ")
            if "translateto" in parameters:
                dom = etree.HTML(description.text)
                translate_dom(dom, parameters["translateto"])
                description.text = to_string(dom)

            parent_obj.append(description)

            if "debug" in parameters and parameters["debug"] == "true":
                p = etree.Element("p")
                i = etree.Element("i")
                i.text = "Session id: %s" % self.session_id
                p.append(i)
                descriptions[0].append(p)

    def _arrange_description_image(self, item: etree._Element, description: etree._Element, parameters: Dict[str, str]):
        nsfw: str = "false"  # safe for work by default
        if "nsfw" in parameters:
            nsfw = parameters["nsfw"]

        if description.text is not None and len(xpath(description, ".//img")) == 0 and to_string(description).find("&lt;img ") == -1:
            # if description does not have a picture, add one from enclosure or media:content tag if any
            img_url: str = self.get_img_url(item)

            title_node: etree._Element = cast(
                etree._Element, self.get_title(item))
            if "translateto" in parameters:
                translate_dom(title_node, parameters["translateto"])
            if img_url == "":
                # uses the ThumbnailHandler to fetch an image from google search images
                img_url = "%s/thumbnails?request=%s&blur=%s" % (
                    self.serving_url_prefix, quote_plus(re.sub(r"</?title[^>]*>", "", to_string(title_node)).strip()), nsfw)

            img = etree.Element("img")
            img.set("src", img_url)
            description.append(img)

        # blur description images
        if nsfw == "true":
            imgs: list = xpath(description, ".//img")
            if len(imgs) > 0:
                for img in imgs:
                    img.attrib["src"] = "%s/thumbnails?url=%s&blur=true" % (
                        self.serving_url_prefix, quote_plus(cast(str, img.attrib["src"])))
            else:
                srcs = re.findall('src="([^"]*)"', cast(str, description.text))
                for src in srcs:
                    description.text = description.text.replace(src, "%s/thumbnails?url=%s&blur=true" % (
                        self.serving_url_prefix, quote_plus(src)))
            self.replace_img_links(
                item, self.serving_url_prefix + "/thumbnails?url=%s&blur=true")

    def _arrange_feed_link(self, item: etree._Element, parameters: Dict[str, str]):
        """arrange feed link, by adding dark and userid parameters if required

        Arguments:
            item {etree._Element} -- rss item
            parameters {Dict[str, str]} -- url parameters, one of them may be the dark boolean
        """
        suffix_url: str = ""
        for parameter in parameters:
            if parameter in ["dark", "debug", "userid", "plain", "hidetitle", "translateto"]:
                suffix_url += "&%s=%s" % (parameter, parameters[parameter])

        if suffix_url != "":
            for link in self.get_links(item):
                self.set_url_from_link(link, "%s%s" % (
                    self.get_url_from_link(link).strip(), suffix_url))

    def _get_source(self, node: etree._Element) -> Optional[etree._Element]:
        """get source url from link in 'url' parameter

        Arguments:
            node {etree} -- rss item node

        Returns:
            etree -- a node having the source url
        """
        n: Optional[etree._Element] = None
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
