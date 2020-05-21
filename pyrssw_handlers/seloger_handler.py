import json
import re

import requests
from lxml import etree

import utils.dom_utils
from handlers.launcher_handler import USER_AGENT
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class SeLogerHandler(PyRSSWRequestHandler):
    """Handler for SeLoger

    Handler name: seloger

    To provide a RSS, the website is webscraped.
    """

    @staticmethod
    def get_handler_name() -> str:
        return "seloger"

    def get_original_website(self) -> str:
        return "http://www.seloger.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict) -> str:
        url = "https://www.seloger.com/list.htm?projects=2,5&types=1,2&natures=1,2,4&places=[{ci:920035}|{ci:920026}|{ci:920004}|{ci:940080}]&price=600000/1280000&rooms=3,4&enterprise=0&qsVersion=1.0&BD=Reprise_Recherche_HP&LISTING-LISTpg=1"

        #content = requests.get(url, headers={'User-Agent': USER_AGENT}).text

        content = open("./pyrssw_handlers/seloger.html", "r").read()
        #dom = etree.HTML(content)
        startIdx = content.find("window[\"initialData\"] = JSON.parse(\"") + len("window[\"initialData\"] = JSON.parse(\"")
        endIdx= content[startIdx:].find("\");\n\n\nwindow[\"tags\"]")
        json_string = content[startIdx:startIdx+endIdx]
        json_obj = json.loads(json_string.encode("utf-8").decode("utf-8").replace("\\u0022", "\""))
        items: str = ""
        if "cards" in json_obj and "list" in json_obj["cards"]:
            for card in json_obj["cards"]["list"]:

                location: str = ""
                if "cityLabel" in card:
                    location = card["cityLabel"]
                if "districtLabel" in card and not card["districtLabel"] is None:
                    location += " - " + card["districtLabel"]

                small_description: str = ""
                if "description" in card:
                    small_description = card["description"]
                
                url_detail: str = ""
                if "serviceUrl" in card:
                    url_detail = card["serviceUrl"]

                price: str = ""
                if "pricing" in card and "price" in card["pricing"]:
                    price = card["pricing"]["price"].replace("\u00A0", " ").replace("\u20AC", "€")
                
                img_url: str =""
                if "photos" in card and isinstance(card["photos"], list) and len(card["photos"]) > 0:
                    img_url = card["photos"][0]

                if price != "":
                    items += """<item>
        <title>%s - %s - %s</title>
        <description>
            <img src="%s"/><p>%s - %s - %s</p>
        </description>
        <link>
            %s?url=%s
        </link>
    </item>""" % (location, price, small_description,
                img_url, location, price, small_description,
                self.url_prefix, url_detail)

        """
        for cards in dom.xpath("//div[contains(@class,\"Card__CardContainer\")]//*[contains(@class,\"DetailTop\")]/.."):

            location: str = ""
            for span in cards.xpath(".//*[contains(@class, \"ContentZone__Address\")]/span"):
                if location != "":
                    location += " - "
                location += span.text

            price: str = ""
            for node in cards.xpath(".//*[contains(@class, \"Price__Label\")]"):
                price = node.text
                break

            small_description: str = ""
            for node in cards.xpath(".//*[contains(@class, \"Card__Description\")]"):
                small_description = node.text
                break

            img_url: str = ""
            for node in cards.xpath(".//*[contains(@class, \"Card__Photo\")]"):
                if "style" in node.attrib:
                    m = re.search(
                        r"background-image:\s*url\('([^'])+'\)", node.attrib["style"])
                    if not m is None:
                        img_url = m.group(1)
                    break

            url_detail: str = ""
            for node in cards.xpath(".//*[contains(@class, \"CoveringLink\")]"):
                if "href" in node.attrib:
                    url_detail = node.attrib["href"]
                    break

            items += " ""<item>
    <title>%s - %s - %s</title>
    <description>
        <img src="%s"/><p>%s - %s - %s</p>
    </description>
    <link>
        %s?url=%s
    </link>
</item>"" " % (location, price, small_description,
              img_url, location, price, small_description,
              self.url_prefix, url_detail)
        """

        return """<rss version="2.0">
    <channel>
        <title>Se Loger</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def get_content(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={"User-Agent": USER_AGENT})
        dom = etree.HTML(page.text)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "BookmarkButtonstyled")]',
            '//*[contains(@class, "TagsWithIcon")]',
            '//button',
            '//svg'
        ])

        content = utils.dom_utils.get_content(
            dom, ['//*[contains(@data-test, "summary")]',
                  "//*[contains(@class,\"ann_expiree g-vspace-400\")]"])  # expired article

        content += utils.dom_utils.get_content(
            dom, ['//*[@id="showcase-description"]'])

        content += "\n<div class=\"images\">\n"
        cpt = 1
        for div in dom.xpath("//div[@data-background]"):
            name = "Image #%d" % cpt
            content += "\t<br/><br/><img src=\"%s\" title=\"%s\" alt=\"%s\" />\n" % (
                div.attrib["data-background"], name, name)
            cpt = cpt + 1
        content += "</div>\n"

        return content
