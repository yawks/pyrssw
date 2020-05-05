from response.RequestHandler import RequestHandler
from lxml import etree
import requests
import string
import urllib
import response.dom_utils


class PyRSSWRequestHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="sport24", original_website="https://sport24.lefigaro.fr/",
                         rss_url="https://sport24.lefigaro.fr/rssfeeds/sport24-%s.xml")

    def get_feed(self, parameters: dict)  -> str:
        if "filter" in parameters and parameters["filter"] == ("tennis" or "football" or "rugby" or "cyclisme" or "golf"):
            # filter only on passed category, eg /sport24/rss/tennis
            feed = requests.get(url=self.rss_url % parameters["filter"], headers={}).text
        else:
            feed = requests.get(url=self.rss_url % "accueil", headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        dom = etree.fromstring(feed)

        xpath_expression = "//item[not(enclosure)]"
        if "filter" in parameters and parameters["filter"] == "flash":
            xpath_expression = "//item[enclosure]"

        response.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        feed = etree.tostring(dom, encoding='unicode')
        feed = feed.replace('<link>', '<link>%s?url=' % self.url_prefix)

        title = ""
        if "filter" in parameters:
            title = " - " + parameters["filter"]

        feed = feed.replace("<title>Sport24 - Toute l'actualite</title>",
                            "<title>Sport24%s</title>" % string.capwords(title))

        return feed

    def get_content(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={})
        content = page.text

        dom = etree.HTML(page.text)
        imgs = dom.xpath("//img[@srcset]")
        imgsrc = ""
        if len(imgs) > 0:
            imgsrc = imgs[0].get("srcset")

        response.dom_utils.delete_nodes(dom.xpath('//*[@class="s24-art-cross-linking"]'))
        response.dom_utils.delete_nodes(dom.xpath('//*[@class="s24-art-pub-top"]'))

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