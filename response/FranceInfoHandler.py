from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import string
import re
import http.cookiejar
import urllib.parse
import response.dom_utils

class PyRSSWRequestHandler(RequestHandler):
    """Handler for french <a href="http://www.franceinfo.fr">France Info</a> website.
    
    Handler name: franceinfo

    RSS parameters:
     - filters : politique, faits-divers, societe, economie, monde, culture, sports, sante, environnement, ...
     
       to invert filtering, prefix it with: ^
       eg : 
         - /franceinfo/rss?filter=politique            #only feeds about politique
         - /franceinfo/rss?filter=politique,societe    #only feeds about politique and societe
         - /franceinfo/rss?filter=^politique,societe   #all feeds but politique and societe
    
    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="franceinfo",
                         original_website="http://www.franceinfo.fr/", rss_url="http://www.franceinfo.fr/rss.xml")

    def getFeed(self, parameters: dict) -> str:
        feed = requests.get(url=self.rss_url, headers={}).text
        
        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)
        feed = feed.replace('<link>', '<link>%s?url=' % (self.url_prefix))

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = lxml.etree.fromstring(feed)

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

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace("data-src", "style='height:100%;width:100%' src")
        content = self._replacePrefixURLs(content)
        dom = lxml.etree.HTML(content)

        response.dom_utils.deleteXPaths(dom, [
            '//*[contains(@class, "block-share")]', 
            '//*[@id="newsletter-onvousrepond"]',
            '//*[contains(@class, "partner-block")]',
            '//*[contains(@class, "a-lire-aussi")]',
            '//aside[contains(@class, "tags")]',
            '//*[contains(@class, "breadcrumb")]',
            '//*[contains(@class, "col-left")]',
            '//*[contains(@class, "col-right")]'
        ])
            
        content = response.dom_utils.getContent(
            dom, ['//div[contains(@class, "content")]', '//div[contains(@class,"article-detail-block")]'])
        
        return content


    def _replacePrefixURLs(self, c: str) -> str:
        content = c.replace("a href='" + self.originalWebsite,
                            "a href='" + self.url_prefix)
        content = content.replace(
            'a href="' + self.originalWebsite, 'a href="' + self.url_prefix)
        content = content.replace('href="/', 'href="' + self.originalWebsite)
        content = content.replace("href='/", "href='" + self.originalWebsite)
        content = content.replace('src="/', 'src="' + self.originalWebsite)
        content = content.replace("src='/", "src='" + self.originalWebsite)

        return content