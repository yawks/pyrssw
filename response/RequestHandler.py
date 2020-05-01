import logging
import datetime
import lxml
import traceback
import urllib.parse

class RequestHandler():
    def __init__(self, url_prefix, handler_name, original_website):
        self.contentType = ""
        self.handlerName = handler_name
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
    def getFeed(self, uri):
        return ''

    #must be overwritten by handlers
    def getContent(self, uri):
        return ''

    def process(self, uri):
        try:
            if uri.find("/rss") == 0:
                self._log("%s /rss requested" % self.handlerName)
                self.contents = self.getFeed(urllib.parse.unquote(uri[len("/rss"):]))
                self.contentType = 'text/xml'
            else:
                self._log("%s content page requested: %s" % (self.handlerName, uri))
                if not uri[1:].startswith("https://") and not uri[1:].startswith("http://"):
                    self.contents = self.getContent(self.originalWebsite + uri)
                else:
                    self.contents = self.getContent(uri)
                self.contentType = self.getContentType()

            self.setStatus(200)
            return True

        except Exception as e:
            self.contents = "<html><body>" + uri + "<br/>"+ str(e) +"<br/><pre>" + traceback.format_exc() + "</pre></body></html>"
            self.setStatus(500)
            return False
    
        def getContentType(self):
            return 'text/html'

    #utility to get html content with header, body and some predefined styles
    #TODO : let background color be customized
    def getWrappedHTMLContent(self, content):
        c = '<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><style>body {color: white;background-color:black;}</style></head><body>'
        c += content
        c += '</body></html>'

        return c