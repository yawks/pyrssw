from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import string
import re
import http.cookiejar

URL_CONNECTION="https://secure.lemonde.fr/sfuser/connexion"

class LeMondeHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, "lemonde", "https://www.lemonde.fr/")
    
    def getFeed(self, uri):
        feed = requests.get(url= "https://www.lemonde.fr/rss/une.xml", headers = {}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="false">', '<link>')
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = feed.replace('<link>https://www.lemonde.fr/', '<link>' + self.url_prefix)
        

        #copy picture url from media to a img tag in description
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '') # I probably do not use etree as I should
        dom = lxml.etree.fromstring(feed)
        for item in dom.xpath("//item"):
            medias = item.xpath(".//*[@url!='']")
            descriptions = item.xpath(".//description")
            if len(medias) > 0 and len(descriptions) > 0:
                descriptions[0].text = '<img src="%s"/>%s' % (medias[0].get('url'), descriptions[0].text)
                

        feed = lxml.etree.tostring(dom, encoding='unicode')
        
        return feed

    def getContent(self, url):
        s = self._authent()

        page = s.get(url = url, headers = super().getUserAgent())
        content = page.text

        dom = lxml.etree.HTML(page.text)

        #self._deleteNodes(dom.xpath('//*[@class="meta meta__social   old__meta-social"]'))
        #self._deleteNodes(dom.xpath('//*[@class="breadcrumb "]'))
        
        contents = dom.xpath('//*[@class="article__wrapper  "]')
        if len(contents) > 0:
            content = "<p><a href='%s'>Source</a></p>%s" % (url, lxml.etree.tostring(contents[0], encoding='unicode'))
            content = content.replace("aria-hidden","dummy")
            content = content.replace("data-format","dummy")
        
        return super().getWrappedHTMLContent(content)
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)

    def _authent(self) -> requests.Session:
        s = requests.Session()
        page = s.get(url=URL_CONNECTION, headers = super().getUserAgent())
        idx = page.text.find("connection[_token]")
        if idx > -1:
            start = page.text[idx+len('connection[_token]" value="'):]
            token = start[0:start.find('"')]
            
            #credits to https://www.freecodecamp.org/news/how-i-scraped-7000-articles-from-a-newspaper-website-using-node-1309133a5070/
            
            data = { #TODO : get email/password from config
                "connection[mail]": "",
                "connection[password]" : "",
                "connection[stay_connected]" : "1",
                "connection[save]" : "",
                "connection[newsletters]" : "[]",
                "connection[_token]" : token}
            headers = {
                "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://secure.lemonde.fr/",
                "Host": "secure.lemonde.fr",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": super().getUserAgent()["User-Agent"],
                "Connection": "keep-alive",
                "Pragma": "no-cache",
                "Referer": URL_CONNECTION
            }
            page = s.post(url = URL_CONNECTION, data = data, headers = headers)
            return s