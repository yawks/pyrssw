from request.pyrssw_content import PyRSSWContent
import string
import re
from typing import List
import requests
from lxml import etree
import json
import base64
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import get_attr_value, text, to_string, xpath

DUGOUT_VIDEO = re.compile(r'(?:https?://embed.dugout.com/v2/\?p=)([^/]*)')


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

        for link in xpath(dom, "//item/link"):
            if link is not None and text(link) is not None:
                link.text = self.get_handler_url_with_parameters(
                    {"url": text(link).strip()})

        feed = to_string(dom)

        title = ""
        if "filter" in parameters:
            title = " - " + parameters["filter"]

        feed = feed.replace("<title>Sport24 - Toute l'actualite</title>",
                            "<title>Sport24%s</title>" % string.capwords(title))

        if description_img != "":
            feed = feed.replace(
                "<description>", "<description>" + description_img)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url, headers={})
        content = page.text

        dom = etree.HTML(page.text)
        title = utils.dom_utils.get_content(dom, ["//h1"])
        imgs = dom.xpath("//img[@srcset]")
        imgsrc = ""
        if len(imgs) > 0:
            imgsrc = imgs[0].get("srcset")

        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="s24-art-cross-linking"]'))
        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="s24-art-pub-top"]'))

        self._process_dugout(session, dom)

        contents = dom.xpath('//*[@class="s24-art__content s24-art__resize"]')
        if len(contents) > 0:
            if imgsrc != "":
                bodies = contents[0].xpath('//*[@class="s24-art-body"]')
                if len(bodies) > 0:
                    img = etree.Element("img")
                    img.set("src", imgsrc)
                    bodies[0].insert(0, img)
            content = to_string(contents[0])
        else:
            content = utils.dom_utils.get_content(dom, [
                '//article[contains(@class,"fig-content")]', #handles golf.lefigaro structure
                '//article[contains(@class,"fig-main")]' #handles lefigaro.fr/sports
            ])

        content = "%s%s" % (title, content)
        return PyRSSWContent(content, """
            #sport24_handler .object-left {
                display: block;
                text-align: center;
                width: auto;
                max-width: fit-content;
                float: left;
                margin: 5px;
            }

            #sport24_handler .object-left img {
                float:none;
                margin:0;
            }

            #sport24_handler .embed {
                clear:both;
            }
            
            #sport24_handler div.object-right {
                text-align:center;
            }
        """)

    def _process_dugout(self, session: requests.Session, dom: etree._Element):
        for iframe in xpath(dom, "//iframe"):
            if "src" in iframe.attrib:
                dugout_ps: List[str] = re.findall(
                    DUGOUT_VIDEO, get_attr_value(iframe, "src"))
                for dugout_p in dugout_ps:
                    try:
                        key = json.loads(base64.b64decode(dugout_p))["key"]
                        dugout_metadata = json.loads(session.get(
                            "https://cdn.jwplayer.com/v2/media/%s" % key).text)

                        p1 = etree.Element("p")
                        video = etree.Element("video")
                        video.set("controls", "")
                        video.set("preload", "auto")
                        # best quality, last index
                        video.set(
                            "poster", dugout_metadata["playlist"][0]["images"][-1]["src"])
                        video.set("width", "100%")

                        source = etree.Element("source")
                        source.set(
                            "src", dugout_metadata["playlist"][0]["sources"][-1]["file"])

                        video.append(source)
                        p1.append(video)

                        p2 = etree.Element("p")
                        p2.text = dugout_metadata["title"]

                        p3 = etree.Element("p")
                        p3.text = dugout_metadata["description"]

                        """
                        parents: List[etree._Element] = xpath(
                            dom, '//*[@class="s24-art__content s24-art__resize"]')

                        if len(parents) > 0:
                            parents[0].append(p1)
                            parents[0].append(p2)
                            parents[0].append(p3)
                        """
                        iframe.getparent().append(p1)
                        iframe.getparent().append(p2)
                        iframe.getparent().append(p3)
                        iframe.getparent().remove(iframe)
                    except Exception as err:
                        self.log_info(
                            "Unable to find dugout video, we ignore this exception and go on (%s)" % repr(err))
                    break
