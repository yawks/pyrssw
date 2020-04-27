from response.RequestHandler import RequestHandler
import lxml.etree
import requests

class EurosportHandler(RequestHandler):
    def __init__(self, prefix, server_name, server_port):
        super().__init__(prefix, server_name, server_port, "eurosport", "https://www.eurosport.fr/")
    
    def getFeed(self, uri):
        feed = requests.get(url= "https://www.eurosport.fr/rss.xml", headers = {}).text
        
        if len(uri) > 1:
            #filter only on passed category, eg /eurosport/rss/tennis
            feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '') # I probably do not use etree as I should
            dom = lxml.etree.fromstring(feed)
            others_than_listed = False
            if uri[1:2] == "^": #other categories than listed
                categories = uri[2:].split(",") #in case of many categories given, separated by comas
                others_than_listed = True
            else:
                categories = uri[1:].split(",") #in case of many categories given, separated by comas
            
            #build xpath expression
            xpath_expression = self._getXpathExpression(categories, others_than_listed)

            self._deleteNodes(dom.xpath(xpath_expression))
            feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    def _getXpathExpression(self, categories, others_than_listed):
        xpath_expression = ""
        for category in categories:
            if others_than_listed:
                if len(xpath_expression) > 0:
                    xpath_expression += " or "
                xpath_expression += "category/text() = '%s'" % category
            else:
                if len(xpath_expression) > 0:
                    xpath_expression += " and "
                xpath_expression += "not(category/text() = '%s')" % category
        return "//rss/channel/item[%s]" % xpath_expression

    def getContent(self, url):
        page = requests.get(url= url, headers = {})
        #dom = lxml.etree.HTML(page.text)
        #self._deleteNodes(dom.xpath('//*[@class="content-info"]'))
        content = page.text

        return super().getWrappedHTMLContent(content)
    

    def _deleteNodes(self, nodes):
        for node in list(nodes):
            node.getparent().remove(node)
