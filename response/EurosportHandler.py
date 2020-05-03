from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import json
import html
import response.dom_utils


class EurosportHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="eurosport",
                         original_website="https://www.eurosport.fr/", rss_url="https://www.eurosport.fr/rss.xml")

    def getFeed(self, parameters: dict)  -> str:
        feed = requests.get(url=self.rss_url, headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = lxml.etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category, eg /eurosport/rss/tennis
            xpath_expression = response.dom_utils.getXpathExpressionForFilters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")


            response.dom_utils.deleteNodes(dom.xpath(xpath_expression))

        # replace video links, they must be processed by getContent
        for link in dom.xpath("//link"):
            if link.text.find("/video.shtml") > -1:
                link.text = "%s?url=%s" % (self.url_prefix, link.text)

        feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    # find in rss file the item having the link_url and returns the description
    def _getRSSLinkDescription(self, link_url):
        description = ""
        feed = requests.get(url=self.rss_url, headers={}).text
        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = lxml.etree.fromstring(feed)
        descriptions = dom.xpath(
            "//item/link/text()[contains(., '%s')]/../../description" % link_url)
        if len(descriptions) > 0:
            description = html.unescape(descriptions[0].text)

        return description

    def getContent(self, url: str, parameters: dict)  -> str:
        content = ""

        if url.find("/video.shtml") > -1 and url.find("_vid") > -1:
            content = self._getVideoContent(url)

        return content

    # video in eurosport website are loaded using some javascript
    # we build here a simplifed page with the rss.xml item description + a video object
    def _getVideoContent(self, url):
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
                    </div>""" % (j["EmbedUrl"], j["Title"], j["VideoUrl"], self._getRSSLinkDescription(url[1:]))
