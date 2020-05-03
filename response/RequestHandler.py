import logging
import datetime
import lxml
import traceback
import urllib.parse
import re

class RequestHandler():
    def __init__(self, url_prefix, handler_name, original_website, rss_url=""):
        self.contentType = ""
        self.handlerName = handler_name
        self.rss_url = rss_url
        self.originalWebsite = original_website
        self.url_prefix = "%s/%s/" % (url_prefix, handler_name)
        self.url_root = url_prefix
        self.logger = logging.getLogger()
        self.contents = ""

    def getUserAgent(self):
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    def _log(self, msg):
        self.logger.info("[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - - " + msg)

    def getContents(self):
        return self.contents

    def read(self):
        return self.contents

    def setStatus(self, status):
        self.status = status

    def getStatus(self):
        return self.status

    def getContentType(self):
        return self.contentType 

    def getType(self):
        return 'static'
    
    #must be overwritten by handlers
    def getFeed(self, parameters: dict):
        return ''

    #must be overwritten by handlers
    def getContent(self, url: str, parameters: dict):
        return ''

    def process(self, url: str):
        try:
            url, parameters = self._getModuleNameFromURL(url)
            if url.find("/rss") == 0:
                self._log("%s /rss requested" % self.handlerName)
                self.contents = self._arrangeFeed(self.getFeed(parameters))
                #add dark request for all rss links
                self.contents = self.contents.replace("%s?" % self.url_prefix, "%s?%s" % (self.url_prefix, self.getDarkParameters(parameters)) )
                self.contentType = 'text/xml'
            else:
                self._log("%s content page requested: %s" % (self.handlerName, url))
                request_url = url
                if "url" in parameters:
                    request_url = parameters["url"]
                if not request_url.startswith("https://") and not request_url.startswith("http://"):
                    self.contents = self.getContent(self.originalWebsite + request_url, parameters)
                else:
                    self.contents = self.getContent(request_url, parameters)

            self.setStatus(200)
            return True

        except Exception as e:
            self.contents = "<html><body>" + url + "<br/>"+ str(e) +"<br/><pre>" + traceback.format_exc() + "</pre></body></html>"
            self.setStatus(500)
            return False
    

    #arrange feed by adding some pictures in description, ...
    def _arrangeFeed(self, content: str) -> str:
        feed = content

        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip() # I probably do not use etree as I should
        feed = re.sub(r'<\?xml-stylesheet [^>]*?>', '', feed).strip()
        dom = lxml.etree.fromstring(feed)

        # copy picture url from enclosure to a img tag in description (or add a generated one)
        for item in dom.xpath("//item"):
            descriptions = item.xpath(".//description")
            if len(descriptions) > 0 and descriptions[0].text.find('<img ') == -1: #
                #if description does not have a picture, add one from enclosure or media:content tag if any
                enclosures = item.xpath(".//enclosure")
                medias = item.xpath(".//*[local-name()='content'][@url]") # media:content tag
                img_url = ""
                if len(enclosures) > 0:
                    img_url = enclosures[0].get('url')
                elif len(medias) > 0:
                    img_url = medias[0].get('url')
                
                if img_url != "":
                    descriptions[0].text = '<img src="%s"/>%s' % (img_url, descriptions[0].text)
                else: #uses the ThumbnailHandler to fetch an image from google search images
                    descriptions[0].text = '<img src="%s/thumbnails?request=%s"/>%s' % (
                        self.url_root, urllib.parse.quote_plus(descriptions[0].text), descriptions[0].text)
        
        feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    #get the module name
    def _getModuleNameFromURL(self, url: str) -> [str, dict]:
        parameters: dict = {}
        new_url: str = url
        parts = url.split('?')
        if len(parts) > 1:
            new_url = parts[0]
            params = parts[1].split('&')
            for param in params:
                keyv = param.split('=')
                if len(keyv) == 2:
                    parameters[urllib.parse.unquote_plus(keyv[0])] = urllib.parse.unquote_plus(keyv[1])

        return new_url, parameters

    #utility to get html content with header, body and some predefined styles
    def getWrappedHTMLContent(self, content: str, parameters: dict):
        dark_style: str = ""
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = "body {color: white;background-color:black;}"
        c = '<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><style>%s</style></head><body>' % dark_style
        c += content
        c += '</body></html>'

        return c
    
    def getDarkParameters(self, parameters: dict) -> str:
        dark_style: str = ""
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = "dark=true&amp;"
        return dark_style