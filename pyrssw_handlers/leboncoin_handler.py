import json
from typing import Optional, Tuple
from urllib.parse import unquote_plus

import requests

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.json_utils import get_node_value_if_exists


class LeBonCoinHandler(PyRSSWRequestHandler):
    """Handler for LeBonCoint, classifieds french website

    Handler name: leboncoin

    RSS parameters:
     - criteria : create a query in the leboncoin website and in the page of results, copy all the URI, ie :
        https://www.leboncoin.fr/

        copy this part:
            recherche/?category=68&locations=Bordeaux__44.85097037673542_-0.5759878158908474_10000&date=20200617-20200619
        and then url encode it, the parameter becomes:
          criteria=recherche%2F%3Fcategory%3D68%26locations%3DBordeaux__44.85097037673542_-0.5759878158908474_10000%26date%3D20200617-20200619
    """

    @staticmethod
    def get_handler_name() -> str:
        return "leboncoin"

    def get_original_website(self) -> str:
        return "https://www.leboncoin.fr/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        items: str = ""
        if "criteria" in parameters:
            url = "%s%s" % (
                self.get_original_website(), unquote_plus(parameters["criteria"]))
            page = session.get(url)
            json_obj: Optional[dict] = self._load_json(
                page.text, "__REDIAL_PROPS__ = ")
            if json_obj is not None and len(json_obj["root"]) > 5 and "data" in json_obj["root"][5] and "ads" in json_obj["root"][5]["data"]:
                for card in json_obj["root"][5]["data"]["ads"]:

                    location: str = self._get_location(card)

                    small_description: str = "%s<br/>%s" % (
                        get_node_value_if_exists(card, "subject"),
                        get_node_value_if_exists(card, "body"))
                    url_detail: str = get_node_value_if_exists(
                        card, "url")
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
        </item>""" % (location, price, small_description.replace("&", "&amp;"),  # NOSONAR
                            img_url, location.replace(
                                "&", "&amp;"), price, small_description.replace("&", "&amp;"),
                            other_imgs,
                            self.get_handler_url_with_parameters({"url": url_detail}))

        return """<rss version="2.0">
    <channel>
        <title>Le bon coin</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def _get_location(self, card: dict) -> str:
        location: str = ""
        if "location" in card and "city" in card["location"]:
            location = card["location"]["city"]

        return location

    def _process_images(self, card: dict) -> Tuple[str, str]:
        img_url: str = ""
        other_imgs: str = ""
        if "images" in card and isinstance(card["images"], dict):
            if "small_url" in card["images"]:
                img_url = card["images"]["small_url"]
            if "urls" in card["images"]:
                for photo_url in card["images"]["urls"]:
                    other_imgs += "<img src=\"%s\" alt=\"Thumbnail\"/>" % photo_url

        return img_url, other_imgs

    def _load_json(self, content: str, prefix: str) -> Optional[dict]:
        """find json in html content page and parse it

        Arguments:
            content {str} -- html content page

        Returns:
            Optional[dict] -- The json object or None
        """
        json_obj: Optional[dict] = None
        start_idx = content.find(prefix) + len(prefix)
        if start_idx > -1:
            end_idx = content[start_idx:].find("</script>")
            if end_idx > -1:
                json_string = "{ \"root\" : %s }" % content[start_idx:start_idx+end_idx].strip(
                )
                json_obj = json.loads(json_string)

        return json_obj

    def _get_price(self, card: dict) -> str:
        price: str = ""
        if "price" in card and isinstance(card["price"], list) and len(card["price"]) > 0:
            price = "%s €" % "{:,}".format(card["price"][0]).replace(",", " ")

        return price

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        content: str = ""

        page = session.get(url=url)
        json_obj: Optional[dict] = self._load_json(
            page.text, "__NEXT_DATA__\" type=\"application/json\">")
        if json_obj is not None and "props" in json_obj["root"] and "pageProps" in json_obj["root"]["props"] and "ad" in json_obj["root"]["props"]["pageProps"]:
            node = json_obj["root"]["props"]["pageProps"]["ad"]
            content = "<p><b>%s</b></p>" % get_node_value_if_exists(
                node, "subject")
            content += "<p><b>%s</b></p>" % self._get_price(node)
            content += "<p>%s</p>" % self._get_location(node)
            content += "<hr/>"
            content += "<b>%s</b>" % get_node_value_if_exists(
                node, "body")
            content += "<hr/>"

            other_imgs: str = ""
            _, other_imgs = self._process_images(node)
            content += other_imgs

        return """
    <div class=\"main-content\">
        %s
    </div>""" % (content)
