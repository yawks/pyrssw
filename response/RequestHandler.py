import logging
import datetime
import lxml
import traceback
import urllib.parse

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
            url, parameters = self._parseURL(url)
            if url.find("/rss") == 0:
                self._log("%s /rss requested" % self.handlerName)
                self.contents = self.getFeed(parameters)
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
    
    def _parseURL(self, url):
        parameters = {}
        new_url = url
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