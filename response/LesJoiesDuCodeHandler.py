from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import re
import response.dom_utils


class PyRSSWRequestHandler(RequestHandler):
    """Handler for Les Joies du Code website.

    Most of the time the feed is enough to display the content of each entry.

    RSS parameters: None 
    """
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="lesjoiesducode",
                         original_website="https://lesjoiesducode.fr/", rss_url="http://lesjoiesducode.fr/rss")

    def getFeed(self, parameters: dict) -> str:
        feed = requests.get(url=self.rss_url, headers={}).text
        feed = feed.replace("<link>", "<link>%s?url=" % self.url_prefix)
        feed = re.sub(
            r'<guid isPermaLink="false">https://lesjoiesducode.fr/\?p=[^<]*</guid>', r"", feed)
        
        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        
        dom = lxml.etree.fromstring(feed)
        for item in dom.xpath('//item'):
            for child in item.getchildren():  # did not find how to xpath content:encoded tag
                if child.tag.endswith("encoded"):
                    c = self._cleanContent(
                        '<div class="blog-post">' + child.text + '</div>')
                    child.text = c  # "<![CDATA[" + c + "]]>"

        return lxml.etree.tostring(dom, encoding='unicode')

    def getContent(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={})
        content = self._cleanContent(page.text)
        return content

    def _cleanContent(self, c):
        content = ""
        if not c is None:
            dom = lxml.etree.HTML(c)
            response.dom_utils.deleteXPaths(dom, [
                '//*[@class="permalink-pagination"]',
                '//*[@class="social-share"]',
                '//*[@class="post-author"]'
            ])

            objs = dom.xpath('//object')
            for obj in objs:
                if obj.attrib["data"].lower().endswith(".gif"):
                    src = obj.attrib["data"]
                    img = lxml.etree.Element("img")
                    img.set("src", src)
                    obj.getparent().getparent().getparent().getparent().append(img)

            response.dom_utils.deleteNodes(dom.xpath('//video'))

            content = response.dom_utils.getContent(
                dom, ['//div[contains(@class, "blog-post")]', '//div[contains(@class,"blog-post-content")]'])

            content = content.replace('<div class="blog-post">', '')
            content = content.replace('<div class="blog-post-content">', '')
            content = content.replace('</div>', '')
            content = re.sub(r'src="data:image[^"]*', '', content)
            content = content.replace("data-src", "style='height:100%;width:100%' src")
            content = re.sub(r'<!--(.*)-->', r"", content, flags=re.S)
        return content
