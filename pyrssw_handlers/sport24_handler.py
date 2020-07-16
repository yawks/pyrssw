import string
import re
import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler


class Sport24Handler(PyRSSWRequestHandler):

    @staticmethod
    def get_handler_name() -> str:
        return "sport24"

    def get_original_website(self) -> str:
        return "https://sport24.lefigaro.fr/"

    def get_rss_url(self) -> str:
        return "https://sport24.lefigaro.fr/rssfeeds/sport24-%s.xml"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        if "filter" in parameters and parameters["filter"] == ("tennis" or "football" or "rugby" or "cyclisme" or "golf"):
            # filter only on passed category, eg /sport24/rss/tennis
            feed = session.get(url=self.get_rss_url() %
                               parameters["filter"], headers={}).text
        else:
            feed = session.get(url=self.get_rss_url() %
                               "accueil", headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        regex = re.compile(r"&(?!amp;|lt;|gt;)")
        myxml = regex.sub("&amp;", feed)
        dom = etree.fromstring(myxml)
        description_img: str = ""

        xpath_expression = "//item[not(enclosure)]"
        if "filter" in parameters and parameters["filter"] == "flash":
            xpath_expression = "//item[enclosure]"
            description_img = "<img src=\"https://pbs.twimg.com/profile_images/932616523285516294/sqt32oQY.jpg\"/>"

        utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        for link in dom.xpath("//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": link.text.strip()})

        feed = etree.tostring(dom, encoding='unicode')

        title = ""
        if "filter" in parameters:
            title = " - " + parameters["filter"]

        feed = feed.replace("<title>Sport24 - Toute l'actualite</title>",
                            "<title>Sport24%s</title>" % string.capwords(title))

        if description_img != "":
            feed = feed.replace(
                "<description>", "<description>" + description_img)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        page = session.get(url=url, headers={})
        content = page.text

        dom = etree.HTML(page.text)
        imgs = dom.xpath("//img[@srcset]")
        imgsrc = ""
        if len(imgs) > 0:
            imgsrc = imgs[0].get("srcset")

        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="s24-art-cross-linking"]'))
        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="s24-art-pub-top"]'))

        contents = dom.xpath('//*[@class="s24-art__content s24-art__resize"]')
        if len(contents) > 0:
            if imgsrc != "":
                bodies = contents[0].xpath('//*[@class="s24-art-body"]')
                if len(bodies) > 0:
                    img = etree.Element("img")
                    img.set("src", imgsrc)
                    bodies[0].append(img)

            content = etree.tostring(contents[0], encoding='unicode')

        return content
