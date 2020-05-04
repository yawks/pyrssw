from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import string
import re
import http.cookiejar
import urllib.parse
import response.dom_utils

class PyRSSWRequestHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="franceinfo",
                         original_website="http://www.franceinfo.fr/", rss_url="http://www.franceinfo.fr/rss.xml")

    def getFeed(self, parameters: dict) -> str:
        feed = requests.get(url=self.rss_url, headers={}).text
        
        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = lxml.etree.fromstring(feed)

        # available filters : international, politique, societe, les-decodeurs, sport, planete, sciences, campus, afrique, pixels, actualites-medias, sante, big-browser, disparitions, podcasts
        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = response.dom_utils.getXpathExpressionForFilters(
                parameters, "link[contains(text(), '/%s/')]", "not(link[contains(text(), '/%s/')])")

            response.dom_utils.deleteNodes(dom.xpath(xpath_expression))

        feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    
    def getContent(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers=super().getUserAgent())
        content = page.text

        dom = lxml.etree.HTML(content)

        response.dom_utils.deleteNodes(
            dom.xpath('//*[contains(@class, "block-share")]'))
        
        content = response.dom_utils.getContent(
            dom, ['//*[contains(@class, "article-detail-block")]'])
        
        return content
