from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import re

class EvilmilkHandler(RequestHandler):
    def __init__(self, prefix, server_name, server_port):
        super().__init__(prefix, server_name, server_port, "evilmilk", "https://www.evilmilk.com/")
    
    def getFeed(self, uri):
        feed = requests.get(url= "https://www.evilmilk.com/rss.xml", headers = {}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = re.sub(r'<link>https?://www.evilmilk.com/', '<link>' + self.url_prefix, feed)
        
        return self._replaceURLs(feed)

    def getContent(self, url):
        page = requests.get(url= url, headers = {})
        dom = lxml.etree.HTML(page.text)

        self._deleteNodes(dom.xpath('//*[@class="content-info"]'))
        self._deleteNodes(dom.xpath('//*[@class="modal"]'))
        self._deleteNodes(dom.xpath('//*[@class="comments text-center"]'))
        self._deleteNodes(dom.xpath('//*[@id="undercomments"]'))
        self._deleteNodes(dom.xpath('//*[@style="padding:10px"]'))
        self._deleteNodes(dom.xpath('//*[@class="hrdash"]'))
        self._deleteNodes(dom.xpath('//*[@class="row heading bottomnav"]'))
        self._deleteNodes(dom.xpath('//*[@id="picdumpnav"]'))
        
        main_bodies = dom.xpath('//*[@id="mainbody"]')
        if len(main_bodies) > 0:
            content = self._replaceURLs(lxml.etree.tostring(main_bodies[0], encoding='unicode'))
        else:
            content = self._replaceURLs(lxml.etree.tostring(dom, encoding='unicode'))
        content = self._cleanContent(content)

        #content = super()._replaceVideosByGifImages(lxml.etree.HTML(content))
        content = content.replace("<video ", "<video controls ")
        content = content.replace('autoplay=""', '')
        content = content.replace('playsinline=""', '')

        return super().getWrappedHTMLContent(content)
    
    def _cleanContent(self, c):
        content = c.replace('<div class="break"/>', '')
        content = content.replace('<div class="tools"/>', '')
        content = re.sub(r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = re.sub(r'<div class="imgbox">(.*)</div>', r"\1", content, flags=re.S)
        return content
    
    def _replaceURLs(self, c):
        content = re.sub(r'href=(["\'])https://www.evilmilk.com/', r'href=\1' + self.url_prefix, c)
        content = re.sub(r'href=(["\'])/', r'href=\1https://www.evilmilk.com/', content)
        content = re.sub(r'src=(["\'])/', r'src=\1https://www.evilmilk.com/', content)
        content = content.replace("<img", "<br/><br/><img")
        return content
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)
