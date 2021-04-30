from abc import ABCMeta, abstractmethod
import logging
from utils.dom_utils import to_string, translate_dom, xpath
from typing import Dict, Optional, cast
import datetime
import re
import html
from urllib.parse import urlparse, quote_plus, parse_qs
from lxml import etree

IMG_URL_REGEX = re.compile(
    r'.*&lt;img src=(?:"|\')([^(\'|")]+).*')


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
    def arrange_feed_top_level_element(self, dom: etree._Element, rss_url_prefix: str, parameters: Dict[str, str], favicon_url: str):
        """Arrange links in channel or feed node

        Args:
            dom (etree._Element): root node of the feed xml
            rss_url_prefix (str): url prefix of /rss handler
            parameters (Dict[str,str]): url parameters
            favicon_url (str): favicon url
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

    @abstractmethod
    def set_thumbnail_item(self, item: etree._Element, img_url: str):
        """Change or create a thumbnail item with the given img_url

        Args:
            item (etree._Element): feed item
            img_url (str): new thumbnail url
        """

    def arrange(self, parameters: Dict[str, str], contents: str, rss_url_prefix: str, favicon_url: str) -> str:
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

                self.arrange_feed_top_level_element(
                    dom, rss_url_prefix, parameters, favicon_url)

                for item in self.get_items(dom):
                    self._arrange_item(item, parameters)
                    self._arrange_feed_link(item, parameters)

                result = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                    to_string(dom)

        except etree.XMLSyntaxError as e:
            logging.getLogger().info(
                "[ %s ] - Unable to parse rss feed for module '%s' (%s), let's proceed anyway",
                datetime.datetime.now().strftime("%Y-%m-%d - %H:%M"),
                self.module_name,
                str(e))

        return result

    def _arrange_item(self, item: etree._Element, parameters: dict):
        descriptions = self.get_descriptions(item)
        thumbnail_url: str = self.get_img_url(item)

        if len(descriptions) > 0:
            description: etree._Element = descriptions[0]
            img_url = self._add_thumbnail_in_description(
                item, description, parameters, thumbnail_url)
            if thumbnail_url == "" and img_url != "":
                self.set_thumbnail_item(item, img_url)

            """
            n = self._get_source(item)
            if n is not None:
                description.append(n)
            """

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

    def _get_thumbnail_url_from_description(self, description: etree._Element) -> str:
        thumbnail_url: str = ""
        imgs = xpath(description, ".//img")
        if len(imgs) > 0:
            thumbnail_url = imgs[0].attrib["url"]
        else:
            m = re.match(IMG_URL_REGEX, to_string(description))
            if m is not None:
                thumbnail_url = m.group(1)

        return thumbnail_url

    def _add_thumbnail_in_description(self, item: etree._Element, description: etree._Element, parameters: Dict[str, str], thumbnail_url: str) -> str:
        img_url: str = thumbnail_url

        nsfw: str = "false" if "nsfw" not in parameters else parameters["nsfw"]
        if description.text is not None:
            description_thumbnail_url: str = self._get_thumbnail_url_from_description(
                description)
            if description_thumbnail_url == "":
                # if description does not have a picture, add one from enclosure or media:content tag if any

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
            else:
                img_url = description_thumbnail_url

        # blur description images
        if nsfw == "true":
            self._manage_blur_image_link(item, description)

        return img_url

    def _manage_blur_image_link(self, item: etree._Element, description: etree._Element):
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
        """arrange feed link, by adding  parameters if required

        Arguments:
            item {etree._Element} -- rss item
            parameters {Dict[str, str]} -- url parameters, one of them may be the dark boolean
        """
        suffix_url: str = ""
        for parameter in parameters:
            if parameter in ["dark", "debug", "plain", "hidetitle", "translateto", "fontsize", "header"]:
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

    def _generated_complete_url(self, handler_url_prefix: str, parameters: Dict[str, str]) -> str:
        complete_url: str = handler_url_prefix
        first = True
        for parameter in parameters:
            complete_url += "?" if first else "&"
            complete_url += "%s=%s" % (parameter, parameters[parameter])
            first = False

        return complete_url
