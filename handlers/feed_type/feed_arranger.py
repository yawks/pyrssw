from abc import ABCMeta, abstractmethod
import logging
from typing import Dict, List, Optional, Tuple, cast
import re
import html
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, quote_plus, parse_qs
from lxml import etree
from handlers.constants import GENERIC_PARAMETERS
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import to_string, xpath

IMG_SRC_REGEX = r'(&lt;|<)img.*src=(?:"|\')([^(\'|")]+)[^>]*>'

HTML_CONTENT_TYPE = "text/html; charset=utf-8"
FEED_XML_CONTENT_TYPE = "application/rss+xml; charset=utf-8"


class FeedArranger(metaclass=ABCMeta):

    def __init__(
        self, module_name: str, serving_url_prefix: Optional[str], session_id: str
    ) -> None:
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
    def arrange_feed_top_level_element(
        self,
        dom: etree._Element,
        rss_url_prefix: str,
        parameters: Dict[str, str],
        favicon_url: str,
    ):
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

    @abstractmethod
    def get_items_tuples(self, dom: etree._Element) -> List[Tuple[str, str, str, str]]:
        """Returns items tuples

        Args:
            dom (etree._Element): etree root dom for feed

        Returns:
            List[Tuple[str, str, str, str]]: article url, item img url, title, item publication date for all items of the feed
        """

    def arrange(
        self,
        parameters: Dict[str, str],
        contents: str,
        rss_url_prefix: str,
        favicon_url: str,
        handler: PyRSSWRequestHandler,
    ) -> Tuple[str, str]:
        result: str = contents
        content_type = FEED_XML_CONTENT_TYPE

        try:
            result: str = contents
            if len(result.strip()) > 0:
                # I probably do not use etree as I should
                result = re.sub(r"<\?xml [^>]*?>", "", result).strip()
                result = re.sub(r"<\?xml-stylesheet [^>]*?>", "", result).strip()

                dom = etree.fromstring(result)

                self.arrange_feed_top_level_element(
                    dom, rss_url_prefix, parameters, favicon_url
                )

                for item in self.get_items(dom):
                    self._arrange_item(item, parameters)
                    self._arrange_feed_link(item, parameters)

                if parameters.get("preview", "") == "true":
                    result, content_type = self.apply_rss_preview(
                        parameters, handler, dom
                    )
                else:
                    result = '<?xml version="1.0" encoding="UTF-8"?>\n' + to_string(dom)

        except etree.XMLSyntaxError as e:
            logging.getLogger().info(
                "[ %s ] - Unable to parse rss feed for module '%s' (%s), let's proceed anyway",
                datetime.now().strftime("%Y-%m-%d - %H:%M"),
                self.module_name,
                str(e),
            )

        return result, content_type

    def _arrange_item(self, item: etree._Element, parameters: dict):
        descriptions = self.get_descriptions(item)
        thumbnail_url: str = self.get_img_url(item)

        if len(descriptions) > 0:
            description: etree._Element = descriptions[0]
            img_url = self._add_thumbnail_in_description(
                item, description, parameters, thumbnail_url
            )
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
            description.text = html.unescape(description_xml.strip()).replace(
                "&nbsp;", " "
            )

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
            m = re.findall(IMG_SRC_REGEX, to_string(description), re.MULTILINE)
            if len(m) > 0 and len(m[0]) > 1:
                thumbnail_url = m[0][1]
            else:
                m = re.findall(IMG_SRC_REGEX, description.text, re.MULTILINE)
                if len(m) > 0 and len(m[0]) > 1:
                    thumbnail_url = m[0][1]

        return thumbnail_url

    def _add_thumbnail_in_description(
        self,
        item: etree._Element,
        description: etree._Element,
        parameters: Dict[str, str],
        thumbnail_url: str,
    ) -> str:
        img_url: str = thumbnail_url

        nsfw: str = "false" if "nsfw" not in parameters else parameters["nsfw"]
        if description.text is not None:
            description_thumbnail_url: str = self._get_thumbnail_url_from_description(
                description
            )
            if description_thumbnail_url == "":
                # if description does not have a picture, add one from enclosure or media:content tag if any

                title_node: etree._Element = cast(etree._Element, self.get_title(item))
                if img_url == "":
                    # TODO no picture
                    pass

                if img_url is not None:
                    img = etree.Element("img")
                    img.set("src", img_url)
                    description.append(img)
            else:
                img_url = description_thumbnail_url

        # blur description images
        if nsfw == "true":
            self._manage_blur_image_link(item, description)

        return img_url

    def _manage_blur_image_link(
        self, item: etree._Element, description: etree._Element
    ):
        imgs: list = xpath(description, ".//img")
        if len(imgs) > 0:
            for img in imgs:
                img.attrib["src"] = "%s/thumbnails?url=%s&blur=true" % (
                    self.serving_url_prefix,
                    quote_plus(cast(str, img.attrib["src"])),
                )
        else:
            srcs = re.findall('src="([^"]*)"', cast(str, description.text))
            for ssrc in srcs:
                description.text = description.text.replace(
                    cast(str, ssrc),
                    "%s/thumbnails?url=%s&blur=true"
                    % (self.serving_url_prefix, quote_plus(ssrc)),
                )
        self.replace_img_links(
            item, self.serving_url_prefix + "/thumbnails?url=%s&blur=true"
        )

    def _arrange_feed_link(self, item: etree._Element, parameters: Dict[str, str]):
        """arrange feed link, by adding  parameters if required

        Arguments:
            item {etree._Element} -- rss item
            parameters {Dict[str, str]} -- url parameters, one of them may be the dark boolean
        """
        suffix_url: str = ""
        for parameter in parameters:
            if parameter in GENERIC_PARAMETERS:
                suffix_url += "&%s=%s" % (parameter, parameters[parameter])

        if suffix_url != "":
            for link in self.get_links(item):
                self.set_url_from_link(
                    link, "%s%s" % (self.get_url_from_link(link).strip(), suffix_url)
                )

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

    def _generated_complete_url(
        self, handler_url_prefix: str, parameters: Dict[str, str]
    ) -> str:
        complete_url: str = handler_url_prefix
        first = True
        for parameter in parameters:
            # do not put parameters having a crypted version
            if parameters.get("%s_crypted" % parameter, "") == "":
                complete_url += "?" if first else "&"
                complete_url += "%s=%s" % (
                    parameter.replace("_crypted", ""),
                    parameters[parameter],
                )
                first = False

        return complete_url

    def apply_rss_preview(
        self, parameters: dict, handler: PyRSSWRequestHandler, dom: etree._Element
    ):
        handler_name = handler.get_handler_name(parameters)
        handler_favicon = handler.get_favicon_url(parameters)
        html = Path("resources/rss_preview.html").read_text()
        html_items = ""
        for url, img_url, title, pub_date in self.get_items_tuples(dom):
            img = ""
            if parameters.get("nsfw", "") == "true":
                img_url = "%s/thumbnails?url=%s&blur=true" % (
                    self.serving_url_prefix,
                    quote_plus(img_url),
                )
            if img_url != "":
                img = f"""
        <img src="{img_url}" class="item-img"/>
"""
            html_items += f"""
<a href="{url}&integrationmode=fullpage" class="item" target="item_content_iframe" onclick="focusItem(this);">
    <div class="item activetitle">
    <div class="item-img-container">
        {img}
    </div>
    <div class="flex-item-title-author-container">
        <div class="item-title-author-container">
        <div class="item-title-fav">
            <div class="item-title">{title}</div>
        </div>
        <div>
            <div class="item-author-date-container">
            <div class="item-author">
                <img src="{handler_favicon}" class="titlesfavicon"/>
                {handler_name}
            </div>
            <div class="item-date">{pub_date}</div>
            </div>
        </div>
        </div>
    </div>
    </div>
</a>
"""

        html = html.replace(
            "#BODYCLASS#", "dark" if parameters.get("theme", "") == "dark" else ""
        )
        html = html.replace("#HANDLER_NAME#", handler_name)
        html = html.replace("#ITEMS#", html_items)

        return html, HTML_CONTENT_TYPE
