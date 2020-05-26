import json
import pickle
import re
from typing import Optional, Tuple
from urllib.parse import unquote_plus

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.json_utils import get_node_value_if_exists


class SeLogerHandler(PyRSSWRequestHandler):
    """Handler for SeLoger, french real estate website

    Handler name: seloger

    RSS parameters:
     - criteria : create a query in the seloger website, and in the page of results, copy all the content after the question mark, ie :
        https://www.seloger.com/list.htm?tri=initial&enterprise=0&idtypebien=2,1&idtt=2,5&naturebien=1,2,4&cp=75

        copy this part:
          tri=initial&enterprise=0&idtypebien=2,1&idtt=2,5&naturebien=1,2,4&cp=75
        and then url encode it, the parameter becomes:
          criteria=tri%3Dinitial%26enterprise%3D0%26idtypebien%3D2%2C1%26idtt%3D2%2C5%26naturebien%3D1%2C2%2C4%26cp%3D75

    To provide a RSS feed, the website is webscraped.
    """

    @staticmethod
    def get_handler_name() -> str:
        return "seloger"

    def get_original_website(self) -> str:
        return "https://www.seloger.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        items: str = ""
        if "criteria" in parameters:
            url = "%slist.htm=?%s" % (
                self.get_original_website(), unquote_plus(parameters["criteria"]))

            content: str = session.get(
                url,
                headers=self._get_headers()
            ).text

            json_obj: Optional[dict] = self._load_json(content)
            if not json_obj is None and "cards" in json_obj and "list" in json_obj["cards"]:
                for card in json_obj["cards"]["list"]:

                    location: str = get_node_value_if_exists(card, "cityLabel")
                    district: str = get_node_value_if_exists(
                        card, "districtLabel")
                    if district != "":
                        location += " - " + district

                    small_description: str = get_node_value_if_exists(
                        card, "description")
                    url_detail: str = get_node_value_if_exists(
                        card, "classifiedURL")
                    price: str = self._get_price(card)

                    img_url: str = ""
                    other_imgs: str = ""
                    img_url, other_imgs = self._process_images(card)

                    if price != "":
                        items += """<item>
            <title>%s - %s - %s</title>
            <description>
                <img src="%s"/><p>%s - %s - %s</p>
                %s
            </description>
            <link>
                %s
            </link>
        </item>""" % (location, price, small_description,
                            img_url, location, price, small_description,
                            other_imgs,
                            self._get_url_prefix(self.get_handler_url_with_parameters({"url": url_detail})))
                with open("tmpfile", "wb") as f:
                    pickle.dump(session, f)

        return """<rss version="2.0">
    <channel>
        <title>Se Loger</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def _get_url_prefix(self, url_detail: str) -> Optional[str]:
        new_url: Optional[str] = url_detail

        if url_detail.find("bellesdemeures.com") > -1:
            # sometimes seloger links are from bellesdemeures website, use the right handler then
            new_url = url_detail.replace("/seloger", "/bellesdemeures")

        return new_url

    def _get_headers(self):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Referer": "https://www.seloger.com/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0"
        }
    """
    de f _get_cookies(self):
        return {
            "AA_Test_House": "a",
            "AA_Test_g": "h",
            "ABtestCreditImmo": "ABtestCreditImmo_VersionB",
            "bannerCookie": "1",
            "beConnectedOrDie": "A",
            "c_m": "undefinedTyped\\%2FBookmarkedTyped`\\%2FBookmarkedundefined",
            "contactvendeur": "0",
            "hideCoronaBanner": "true",
            "s_cc": "true",
            "uuid230": "1a2052a9-62e5-4bca-a104-b4edf5d7ebf1",
            "visitId": "%d-%d" % (random.randrange(100000000000, 999999999999), random.randrange(1000000000, 9999999999))
        }
    """
    def _process_images(self, card: dict) -> Tuple[str, str]:
        img_url: str = ""
        other_imgs: str = ""
        if "photos" in card and isinstance(card["photos"], list):
            for photo_url in card["photos"]:
                if img_url == "":
                    img_url = photo_url
                other_imgs += "<img src=\"%s\" alt=\"Thumbnail\"/>" % photo_url

        return img_url, other_imgs

    def _get_price(self, card: dict) -> str:
        price: str = ""
        if "pricing" in card and "price" in card["pricing"]:
            price = card["pricing"]["price"].replace(
                "\u00A0", " ").replace("\u20AC", "€")

        return price

    def _load_json(self, content: str) -> Optional[dict]:
        """find json in html content page and parse it

        Arguments:
            content {str} -- html content page

        Returns:
            Optional[dict] -- The json object or None
        """
        json_obj: Optional[dict] = None
        start_idx = content.find(
            "window[\"initialData\"] = JSON.parse(\"") + len("window[\"initialData\"] = JSON.parse(\"")
        if start_idx > -1:
            end_idx = content[start_idx:].find("window[\"tags\"]")
            if end_idx > -1:
                json_string = content[start_idx:start_idx+end_idx].strip()
                json_string = re.sub(r'"\);$', r"", json_string, flags=re.S)
                json_obj = json.loads(json_string.encode(
                    "utf-8").decode("utf-8").replace("\\u0022", "\""))

        return json_obj

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        page = session.get(url=url,
                           headers=self._get_headers())
        dom = etree.HTML(page.text)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "BookmarkButtonstyled")]',
            '//*[contains(@class, "TagsWithIcon")]',
            '//button',
            '//svg'
        ])
        # move images to a readable node
        cpt = 1
        nodes = dom.xpath("//*[contains(@class,\"ShowMoreText\")]//p")
        if len(nodes) > 0:
            node = nodes[0]
            for div in dom.xpath("//div[@data-background]"):
                new_img = etree.Element("img")
                new_img.attrib["src"] = div.attrib["data-background"]
                new_img.attrib["alt"] = "Images #%d" % cpt

                node.append(new_img)
                node.append(etree.Element("br"))
                node.append(etree.Element("br"))
                cpt = cpt + 1

        content = utils.dom_utils.get_content(
            dom, ['//*[contains(@data-test, "summary")]',
                  "//*[contains(@class,\"ann_expiree g-vspace-400\")]"])  # expired article

        content += utils.dom_utils.get_content(
            dom, ['//*[@id="showcase-description"]'])

        return content
