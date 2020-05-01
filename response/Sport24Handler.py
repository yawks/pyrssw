from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import string
import urllib

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

        #copy picture url from enclosure to a img tag in description (or add a generated one)
        for item in dom.xpath("//item"):
            enclosures = item.xpath(".//enclosure")
            descriptions = item.xpath(".//description")
            if len(descriptions) > 0:
                if len(enclosures) > 0:
                    descriptions[0].text = '<img src="%s"/>%s' % (enclosures[0].get('url'), descriptions[0].text)
                else:
                    descriptions[0].text = '<img src="%s/thumbnails/%s"/>%s' % (self.url_root, urllib.parse.quote_plus(descriptions[0].text), descriptions[0].text)

        feed = lxml.etree.tostring(dom, encoding='unicode')
        feed = feed.replace('<link>https://sport24.lefigaro.fr/', '<link>' + self.url_prefix)

        title = ""
        if len(uri) > 1:
            title = " - " + uri[1:]

        feed = feed.replace("<title>Sport24 - Toute l'actualite</title>", "<title>Sport24%s</title>" % string.capwords(title))
        
        return feed

    def getContent(self, url):
        page = requests.get(url= url, headers = {})
        content = page.text

        dom = lxml.etree.HTML(page.text)
        imgs = dom.xpath("//img[@srcset]")
        img = ""
        if len(imgs) > 0:
            imgsrc = imgs[0].get("srcset")

        self._deleteNodes(dom.xpath('//*[@class="s24-art-cross-linking"]'))
        self._deleteNodes(dom.xpath('//*[@class="s24-art-pub-top"]'))
        
        contents = dom.xpath('//*[@class="s24-art__content s24-art__resize"]')
        if len(contents) > 0:

            bodies = contents[0].xpath('//*[@class="s24-art-body"]')
            if len(bodies) > 0:
                img = lxml.etree.Element("img")
                img.set("src", imgsrc)
                bodies[0].append(img)

            content = lxml.etree.tostring(contents[0], encoding='unicode')
        
        return super().getWrappedHTMLContent(content)
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)
