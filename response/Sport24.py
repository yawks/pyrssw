from response.RequestHandler import RequestHandler
import lxml.etree
import requests

class Sport24Handler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, "sport24", "https://sport24.lefigaro.fr/")
    
    def getFeed(self, uri):
        if len(uri) > 1 and uri[1:] == ("tennis" or "football" or "rugby" or "cyclisme" or "golf"):
            #filter only on passed category, eg /sport24/rss/tennis
            feed = requests.get(url= "https://sport24.lefigaro.fr/rssfeeds/sport24-%s.xml" % uri[1:], headers = {}).text
        else:
            feed = requests.get(url= "https://sport24.lefigaro.fr/rssfeeds/sport24-accueil.xml", headers = {}).text
                
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '') # I probably do not use etree as I should
        dom = lxml.etree.fromstring(feed)

        xpath_expression = "//item[not(enclosure)]"
        if len(uri) > 1 and uri[1:] == "flash":
            xpath_expression = "//item[enclosure]"
        
        self._deleteNodes(dom.xpath(xpath_expression))
        feed = lxml.etree.tostring(dom, encoding='unicode')

        feed = feed.replace('<link>https://sport24.lefigaro.fr/', '<link>' + self.url_prefix)
        
        return feed

    def getContent(self, url):
        page = requests.get(url= url, headers = {})
        content = page.text

        dom = lxml.etree.HTML(page.text)
        imgs = dom.xpath("//img[@srcset]")
        img = ""
        if len(imgs) > 0:
            img = lxml.etree.tostring(imgs[0], encoding='unicode')

        self._deleteNodes(dom.xpath('//*[@class="s24-art-cross-linking"]'))
        self._deleteNodes(dom.xpath('//*[@class="s24-art-pub-top"]'))
        
        contents = dom.xpath('//*[@class="s24-art__content s24-art__resize"]')
        if len(contents) > 0:
            content = lxml.etree.tostring(contents[0], encoding='unicode')
        
        

        content = content.replace('class="s24-art__content s24-art__resize"', "id='mainbody'") + img
        return super().getWrappedHTMLContent(content)
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)
