from typing import List
from urllib.parse import unquote_plus

import requests
import json

from utils.json_utils import get_node_value_if_exists
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class BienIciHandler(PyRSSWRequestHandler):
    """Handler for BienIci, french real estate website

    Handler name: bienici

    RSS parameters:
     - criteria : create a query in the bienici website, and in the page of results, copy all the content after the question mark, ie :
        https://www.bienici.com/recherche/achat/bordeaux-33000/2-pieces-et-plus?prix-max=500000&balcon=oui

        in the network pane of webdeveloper view (F12), look for realEstateAds.json query to get the full query:
          realEstateAds.json?filters={"size":24,"from":0,"filterType":"buy","propertyType":["house","flat"],"maxPrice":1250000,"minRooms":3,"page":1,"resultsPerPage":24,"maxAuthorizedResults":2400,"sortBy":"relevance","sortOrder":"desc","onTheMarket":[true],"limit":"iqwiHognJ?i{sDpoWhB?ttsD","propertyType.base":["programme"],"programmeWith3dFirst":true,"showAllModels":false,"blurInfoType":["disk","exact"],"zoneIdsByTypes":{"zoneIds":["-91775","-91641","-91768","-108346"]}}&extensionType=extendedIfNoResult
        and then url encode it, the parameter becomes:
          criteria=realEstateAds.json?filters=%7B%22size%22%3A24%2C%22from%22%3A0%2C%22filterType%22%3A%22buy%22%2C%22propertyType%22%3A%5B%22house%22%2C%22flat%22%5D%2C%22maxPrice%22%3A1250000%2C%22minRooms%22%3A3%2C%22page%22%3A1%2C%22resultsPerPage%22%3A24%2C%22maxAuthorizedResults%22%3A2400%2C%22sortBy%22%3A%22relevance%22%2C%22sortOrder%22%3A%22desc%22%2C%22onTheMarket%22%3A%5Btrue%5D%2C%22limit%22%3A%22iqwiHognJ%3Fi%7BsDpoWhB%3FttsD%22%2C%22propertyType.base%22%3A%5B%22programme%22%5D%2C%22programmeWith3dFirst%22%3Atrue%2C%22showAllModels%22%3Afalse%2C%22blurInfoType%22%3A%5B%22disk%22%2C%22exact%22%5D%2C%22zoneIdsByTypes%22%3A%7B%22zoneIds%22%3A%5B%22-91775%22%2C%22-91641%22%2C%22-91768%22%2C%22-108346%22%5D%7D%7D&extensionType=extendedIfNoResult
    """

    @staticmethod
    def get_handler_name() -> str:
        return "bienici"

    def get_original_website(self) -> str:
        return "https://www.bienici.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        items: str = ""
        if "criteria" in parameters:
            url = "%s%s" % (
                self.get_original_website(), unquote_plus(parameters["criteria"]))
            page = session.get(url)

            json_obj = json.loads(page.text)
            if json_obj is not None and "realEstateAds" in json_obj:
                for entry in json_obj["realEstateAds"]:

                    location: str = get_node_value_if_exists(
                        entry, "city")
                    price: str = self._get_price(entry)
                    small_description: str = get_node_value_if_exists(
                        entry, "title").replace("<br>", "<br/>").replace("&", "&amp;")
                    description: str = get_node_value_if_exists(
                        entry, "description").replace("<br>", "<br/>").replace("&", "&amp;")
                    url_detail: str = "https://www.bienici.com/realEstateAd.json?id=%s" % get_node_value_if_exists(
                        entry, "id")
                    img_urls: List[str] = self._get_img_urls(entry)

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
        <title>Bien Ici</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def _get_price(self, entry: dict) -> str:
        price: str = ""
        p = get_node_value_if_exists(
            entry, "price")
        if isinstance(p, int):
            price = "%s €" % "{:,}".format(p).replace(",", " ")

        return price

    def _get_img_urls(self, entry: dict) -> List[str]:
        img_urls: List[str] = []
        if "photos" in entry and isinstance(entry["photos"], list):
            for photo in entry["photos"]:
                if "url_photo" in photo:
                    img_urls.append(photo["url_photo"])

        return img_urls

    def _build_imgs(self, img_urls: List[str]) -> str:
        imgs: str = ""
        for img_url in img_urls:
            imgs += "<img src=\"%s\"/><br/><br/>" % img_url

        return imgs

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        content: str = ""

        content = session.get(url=url).text

        json_obj = json.loads(content)
        if json_obj is not None:
            content = "<p><b>%s</b></p>" % get_node_value_if_exists(
                json_obj, "title")
            content += "<p><b>%s</b></p>" % self._get_price(json_obj)
            content += "<p>%s - %s</p>" % (get_node_value_if_exists(
                json_obj, "postalCode"), get_node_value_if_exists(json_obj, "city"))
            content += "<hr/>"
            content += "<b>%s</b>" % get_node_value_if_exists(
                json_obj, "description")
            content += "<hr/>"
            content += self._build_imgs(self._get_img_urls(json_obj))

        return """
    <div class=\"main-content\">
        %s
    </div>""" % (content)
