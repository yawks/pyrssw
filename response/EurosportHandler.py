from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import json
import html

class EurosportHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, "eurosport", "https://www.eurosport.fr/")
        self.feed = "https://www.eurosport.fr/rss.xml"
    
    def getFeed(self, uri):
        feed = requests.get(url= self.feed, headers = {}).text

        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '') # I probably do not use etree as I should
        dom = lxml.etree.fromstring(feed)
        
        if len(uri) > 1:
            #filter only on passed category, eg /eurosport/rss/tennis
            others_than_listed = False
            if uri[1:2] == "^": #other categories than listed
                categories = uri[2:].split(",") #in case of many categories given, separated by comas
                others_than_listed = True
            else:
                categories = uri[1:].split(",") #in case of many categories given, separated by comas
            
            #build xpath expression
            xpath_expression = self._getXpathExpression(categories, others_than_listed)

            self._deleteNodes(dom.xpath(xpath_expression))

        #replace video links, they must be processed by getContent
        for link in dom.xpath("//link"):
            if link.text.find("/video.shtml") > -1:
                link.text = "%s%s" % (self.url_prefix, link.text)


        feed = lxml.etree.tostring(dom, encoding='unicode')

            
        return feed

    def _getXpathExpression(self, categories, others_than_listed):
        xpath_expression = ""
        for category in categories:
            if others_than_listed:
                if len(xpath_expression) > 0:
                    xpath_expression += " or "
                xpath_expression += "category/text() = '%s'" % category
            else:
                if len(xpath_expression) > 0:
                    xpath_expression += " and "
                xpath_expression += "not(category/text() = '%s')" % category
        return "//rss/channel/item[%s]" % xpath_expression

    #find in rss file the item having the link_url and returns the description
    def _getRSSLinkDescription(self, link_url):
        description = ""
        feed = requests.get(url= self.feed, headers = {}).text
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '') # I probably do not use etree as I should
        dom = lxml.etree.fromstring(feed)
        descriptions = dom.xpath("//item/link/text()[contains(., '%s')]/../../description" % link_url)
        if len(descriptions) >0:
            description = html.unescape(descriptions[0].text)

        return description


    def getContent(self, url):
        content = ""

        if url.find("/video.shtml") > -1 and url.find("_vid") >-1:
            content = self._getVideoContent(url)

        return super().getWrappedHTMLContent(content)

    # video in eurosport website are loaded using some javascript
    # we build here a simplifed page with the rss.xml item description + a video object
    def _getVideoContent(self, url):
        vid = url[url.find("_vid")+len("_vid"):]
        vid = vid[:vid.find('/')]
        page = requests.get(url = "https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % vid, headers = {})
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
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)
