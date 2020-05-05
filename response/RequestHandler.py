import logging
import datetime
import lxml
import traceback
import urllib.parse
import re

HTML_CONTENT_TYPE = "text/html; charset=utf-8"

class RequestHandler():
    """Main instance for every handler.

    getFeed, getContent and optionnally getContentType must be overridden by every new Handlers.

    - getFeed :
        Takes a dictionary of parameters and must return the xml of the rss feed

    - getContent :
        Takes an url and a dictionary of parameters and must return the result content.
        If the content returned is not HTML, the function getContentType must also be overridden (see ThumbnailsHandler.py)
    """
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

    def getContents(self) -> str:
        return self.contents

    def read(self) -> str:
        return self.contents

    def setStatus(self, status: int):
        self.status = status

    def getStatus(self) -> int:
        return self.status

    def getContentType(self)  -> str:
        return self.contentType 

    def getType(self)  -> str:
        return 'static'
    
    #must be overwritten by handlers
    def getFeed(self, parameters: dict)  -> str:
        return ''

    #must be overwritten by handlers
    def getContent(self, url: str, parameters: dict)  -> str:
        return ''

    def process(self, url: str) -> bool:
        """process the url, finds the handler to use depending on the url"""
        try:
            url, parameters = self._getModuleNameFromURL(url)
            if url.find("/rss") == 0:
                self._log("%s /rss requested" % self.handlerName)
                self.contents = self._arrangeFeed(self.getFeed(parameters))
                #add dark request for all rss links
                self.contents = self.contents.replace("%s?" % self.url_prefix, "%s?%s" % (self.url_prefix, self.getDarkParameters(parameters)) )
                self.contentType = "text/xml; charset=utf-8"
            else:
                self._log("%s content page requested: %s" % (self.handlerName, url))
                request_url = url
                self.contentType = HTML_CONTENT_TYPE #default contentType, can be overridden by handlers
                if "url" in parameters:
                    request_url = parameters["url"]
                if not request_url.startswith("https://") and not request_url.startswith("http://"):
                    self.contents = self.getContent(self.originalWebsite + request_url, parameters)
                else:
                    self.contents = self.getContent(request_url, parameters)
                
                if self.getContentType() == HTML_CONTENT_TYPE: #in case of overridden content type, not very clean :S
                    self._wrappedHTMLContent(parameters)

            self.setStatus(200)
            return True

        except Exception as e:
            self.contents = "<html><body>" + url + "<br/>"+ str(e) +"<br/><pre>" + traceback.format_exc() + "</pre></body></html>"
            self.contentType = "text/html; utf-8"
            self.setStatus(500)
            return False
    

    
    def _arrangeFeed(self, content: str) -> str:
        """arrange feed by adding some pictures in description, ..."""
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

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + feed

    def _getModuleNameFromURL(self, url: str) -> [str, dict]:
        """get the module name and the url requested from the url"""
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

    def _wrappedHTMLContent(self, parameters: dict):
        """wrap the html content with header, body and some predefined styles"""
        dark_style: str = ""
        source: str = ""
        if "url" in parameters:
            source = "<em><a href='%s'>Source</em>" % parameters["url"]
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = """@media (prefers-color-scheme: dark) {
                                body {
                                    background-color: #111;
                                    color: #ccc;
                                }
                                a { 
                                    color:#0080ff
                                }
                                * {
                                    font-family: "Marr Sans",Helvetica,Arial,Roboto,sans-serif
                                }
                            }
                        """

        #TODO remove head and body if previously exists and logs it

        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <style>%s</style>
                        </head>
                        <body>
                            %s
                            <br/>
                            <br/>
                            <hr/>
                            %s
                        </body>
                    </html>""" % (dark_style, self.contents, source)
    
    def getDarkParameters(self, parameters: dict) -> str:
        """get the url parameter if dark=true is defined in parameters"""
        dark_style: str = ""
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = "dark=true&amp;"
        return dark_style