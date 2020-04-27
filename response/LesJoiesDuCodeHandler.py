from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import re

class LesJoiesDuCodeHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, "lesjoiesducode", "https://lesjoiesducode.fr/")

    
    def getFeed(self, uri):
        feed = requests.get(url= "http://lesjoiesducode.fr/rss", headers = {}).text
        feed = feed.replace("<link>https://lesjoiesducode.fr/", "<link>" + self.url_prefix)
        feed = re.sub(r'<guid isPermaLink="false">https://lesjoiesducode.fr/\?p=[^<]*</guid>', r"", feed)

        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '')

        dom = lxml.etree.fromstring(feed)
        for item in dom.xpath('//item'):
            for child in item.getchildren(): # did not find how to xpath content:encoded tag
                if child.tag.endswith("encoded"):
                    c = self._cleanContent('<div class="blog-post">' + child.text + '</div>')
                    child.text = c #"<![CDATA[" + c + "]]>"

        return lxml.etree.tostring(dom, encoding='unicode')
    
    def getContent(self, url):
        page = requests.get(url= url, headers = {})
        content = self._cleanContent(page.text)
        self.contentType = 'text/html'
        return content

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)

    def _cleanContent(self, c):
        content = ""
        if not c is None:
            dom = lxml.etree.HTML(c)
            self._deleteNodes(dom.xpath('//*[@class="permalink-pagination"]'))
            self._deleteNodes(dom.xpath('//*[@class="social-share"]'))
            self._deleteNodes(dom.xpath('//*[@class="post-author"]'))

            gif = None
            objs = dom.xpath('//object')
            for obj in objs:
                if obj.attrib["data"].lower().endswith(".gif"):
                    gif = obj.attrib["data"]
                    break

            self._deleteNodes(dom.xpath('//video'))
            
            content = lxml.etree.tostring(dom.xpath('//*[@class="blog-post"]')[0], encoding='unicode')
            content = content.replace('<div class="blog-post">', '')
            content = content.replace('<div class="blog-post-content">', '')
            content = content.replace('</div>', '')
            if not gif is None:
                if content.find("<p/>") > -1:
                    content = content.replace('<p/>', '<img src="'+gif+'"/>')
                else:
                    content = content.replace('<p>', '<p><img src="'+gif+'"/>')
            content = re.sub(r'<!--(.*)-->', r"", content, flags=re.S)
        return content

    
