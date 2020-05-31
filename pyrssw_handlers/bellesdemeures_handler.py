from typing import List, Optional
from urllib.parse import unquote_plus

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class BellesDemeuresHandler(PyRSSWRequestHandler):
    """Handler for Belles demeures, french real estate website

    Handler name: bellesdemeures

    RSS parameters:
     - criteria : create a query in the bellesdemeures website, and in the page of results, copy all the content after the question mark, ie :
        https://www.bellesdemeures.com/recherche?ci=330063&pxmax=5000000&idtt=2&tri=Selection

        copy this part:
          recherche?ci=330063&pxmax=5000000&idtt=2&tri=Selection
        and then url encode it, the parameter becomes:
          criteria=recherche%3Fci%3D330063%26pxmax%3D5000000%26idtt%3D2%26tri%3DSelection
    """

    @staticmethod
    def get_handler_name() -> str:
        return "bellesdemeures"

    def get_original_website(self) -> str:
        return "https://www.bellesdemeures.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        items: str = ""
        if "criteria" in parameters:
            url = "%s%s" % (
                self.get_original_website(), unquote_plus(parameters["criteria"]))
            page = session.get(url)

            dom = etree.HTML(page.text)
            if dom is not None:
                for card in dom.xpath("//*[contains(@class,\"annonceGold\")]"):

                    location: str = self._get_location(card)
                    price: str = self._get_price(card)
                    small_description: str = self._get_small_description(card)
                    description: str = self._get_description(card)
                    url_detail: str = self._get_url(card)
                    img_urls: List[str] = self._get_img_urls(card)

                    if small_description != "" and price != "":
                        items += """<item>
                <title>%s - %s - %s</title>
                <description>
                    <img src="%s"/><p>%s - %s - %s</p>
                    %s
                    %s
                </description>
                <link>
                    %s
                </link>
            </item>""" % (location, price, small_description,
                          img_urls[0] if len(
                              img_urls) > 0 else "", location, price, small_description,
                          description,
                          self._build_imgs(img_urls),
                          self.get_handler_url_with_parameters({"url": url_detail}))

        return """<rss version="2.0">
    <channel>
        <title>Belles Demeures</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def _get_location(self, card: etree.HTML) -> str:
        location: str = ""
        for node in card.xpath(".//*[contains(@class, \"location\")]"):
            location = node.text.strip()
            break

        return location

    def _get_small_description(self, card: etree.HTML) -> str:
        small_description: str = ""
        descr_node: Optional[etree._Element] = utils.dom_utils.get_first_node(
            card, [".//div[contains(@class, \"more\")]"])
        if descr_node is not None:
            small_description = " ".join(
                "".join(descr_node.itertext()).strip().replace("\r\n", " - ").split())

        return small_description

    def _get_description(self, card: etree.HTML) -> str:
        description: str = ""
        for node in card.xpath(".//div[contains(@class, \"desc\")]"):
            description = node.text.strip()
            break

        return description

    def _get_price(self, card: etree.HTML) -> str:
        price: str = ""
        for node in card.xpath(".//*[contains(@class, \"price\")]"):
            price = node.text.strip()
            break

        return price

    def _get_img_urls(self, card: etree.HTML) -> List[str]:
        img_urls: List[str] = []
        for node in card.xpath(".//*[@data-slides]"):
            for url in node.attrib["data-slides"].split(";"):
                img_urls.append(url)
            break

        return img_urls

    def _get_url(self, card: etree.HTML) -> str:
        url_detail: str = ""
        for node in card.xpath(".//a[contains(@class, \"details\")]"):
            if "href" in node.attrib:
                url_detail = node.attrib["href"]
                break

        return url_detail

    def _build_imgs(self, img_urls: List[str]) -> str:
        imgs: str = ""
        for img_url in img_urls:
            imgs += "<img src=\"%s\"/><br/><br/>" % img_url

        return imgs

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        content: str = ""

        content = session.get(url=url).text

        dom = etree.HTML(content)
        if dom is not None:

            descriptions = dom.xpath(
                "//*[contains(@class, \"detailDescSummary\")]")
            if len(descriptions) > 0:
                # move images to a readable node
                node = descriptions[0]
                node.append(etree.Element("br"))
                cpt = 1
                for li in dom.xpath("//li[contains(@class,\"carouselListItem\")][@data-srco]"):
                    new_img = etree.Element("img")
                    new_img.attrib["src"] = li.attrib["data-srco"].replace(
                        "182x136", "800x600")
                    new_img.attrib["alt"] = "Images #%d" % cpt

                    node.append(new_img)
                    node.append(etree.Element("br"))
                    node.append(etree.Element("br"))
                    cpt = cpt + 1

            content = utils.dom_utils.get_content(
                dom, ['//*[contains(@class, "detailDescSummary")]'])
            content += utils.dom_utils.get_content(
                dom, ['//*[contains(@class, "detailInfos")]'])

        return """
    <div class=\"main-content\">
        %s
    </div>""" % (content)
