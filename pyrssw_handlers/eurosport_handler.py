import html
import json

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler


class EurosportHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.eurosport.fr">Eurosport</a> website.

    Handler name: eurosport

    RSS parameters:
     - filter : tennis, football, rugby
       to invert filtering, prefix it with: ^
       eg :
         - /eurosport/rss?filter=tennis             #only feeds about tennis
         - /eurosport/rss?filter=football,tennis    #only feeds about football and tennis
         - /eurosport/rss?filter=^football,tennis   #all feeds but football and tennis
    
    Content:
        Content remains Eurosport links except for video pages.
        Video pages in the eurosport website are dynamically built using some javascript, the handler provide a simple page with a HTML5 video object embedding the video.
    """
    
    @staticmethod
    def get_handler_name() -> str:
        return "eurosport"

    def get_original_website(self) -> str:
        return "https://www.eurosport.fr/"
    
    def get_rss_url(self) -> str:
        return "https://www.eurosport.fr/rss.xml"

    def get_feed(self, parameters: dict)  -> str:
        feed = requests.get(url=self.get_rss_url(), headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category, eg /eurosport/rss/tennis
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        # replace video links, they must be processed by getContent
        for link in dom.xpath("//link"):
            if link.text.find("/video.shtml") > -1:
                link.text = "%s?url=%s" % (self.url_prefix, link.text)

        feed = etree.tostring(dom, encoding='unicode')

        return feed

    def _get_rss_link_description(self, link_url: str) -> str:
        """find in rss file the item having the link_url and returns the description"""
        description = ""
        feed = requests.get(url=self.get_rss_url(), headers={}).text
        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)
        descriptions = dom.xpath(
            "//item/link/text()[contains(., '%s')]/../../description" % link_url)
        if len(descriptions) > 0:
            description = html.unescape(descriptions[0].text)

        return description

    def get_content(self, url: str, parameters: dict)  -> str:
        content = ""

        if url.find("/video.shtml") > -1 and url.find("_vid") > -1:
            content = self._get_video_content(url)
        else:
            content = requests.get(url, headers={}).text

        return content

    def _get_video_content(self, url: str) -> str:
        """ video in eurosport website are loaded using some javascript
            we build here a simplifed page with the rss.xml item description + a video object"""
        vid = url[url.find("_vid")+len("_vid"):]
        vid = vid[:vid.find('/')]
        page = requests.get(
            url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % vid, headers={})
        j = json.loads(page.text)

        return """
                    <div>
                        <p>
                            <a href="%s"><p>%s</p></a>
                            <video controls="" preload="auto">
                                <source src="%s" />
                            </video>
                        </p>
                        <p>%s</p>
                    </div>""" % (j["EmbedUrl"], j["Title"], j["VideoUrl"], self._get_rss_link_description(url[1:]))