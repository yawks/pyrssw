import logging
import datetime
import lxml
import traceback
import urllib.parse

class RequestHandler():
    def __init__(self, prefix, server_name, server_port, handler_name, original_website):
        self.contentType = ""
        self.handlerName = handler_name
        self.originalWebsite = original_website
        self.url_prefix = "%s://%s:%s/%s/" % (prefix, server_name, str(server_port), self.handlerName)
        #self.video_url_prefix = prefix + "://" + server_name + ":" + str(server_port) + "/video/"
        self.logger = logging.getLogger()
        self.contents = ""
        
    def _log(self, msg):
        self.logger.info("[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - - " + msg)

    #def getVideoUrlPrefix(self):
    #    return self.video_url_prefix

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
                self.contents = self.getContent(self.originalWebsite + uri)

            self.setStatus(200)
            return True

        except Exception as e:
            self.contents = "<html><body>" + uri + "<br/>"+ str(e) +"<br/><pre>" + traceback.format_exc() + "</pre></body></html>"
            self.setStatus(500)
            return False
    
    #utility to get html content with header, body and some predefined styles
    #TODO : let background color be customized
    def getWrappedHTMLContent(self, content):
        c = '<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8" /><style>#mainbody {color: white;background-color:black;}</style></head><body>'
        c += content
        c += '</body></html>'

        return c

    '''
    def _replaceVideosByGifImages(self, dom):
        videos = dom.xpath('//video')
        for video in videos:
            gif = None
            sources = video.xpath('.//source')
            for source in sources:
                gif = source.attrib["src"]
                if source.attrib["src"].lower().endswith(".gif"):
                    break
            if not gif is None:
                parent = video.getparent()
                parent.remove(video)
                img = lxml.etree.SubElement(parent, "img")
                img.attrib["src"] = self.video_url_prefix + gif + ".gif"
        
        return ""#lxml.etree.tostring(dom, encoding='unicode')
    '''