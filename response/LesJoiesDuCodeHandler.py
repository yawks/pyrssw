from response.RequestHandler import RequestHandler
from lxml import etree
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

    def get_feed(self, parameters: dict) -> str:
        feed = requests.get(url=self.rss_url, headers={}).text
        feed = feed.replace("<link>", "<link>%s?url=" % self.url_prefix)
        feed = re.sub(
            r'<guid isPermaLink="false">https://lesjoiesducode.fr/\?p=[^<]*</guid>', r"", feed)
        
        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        
        dom = etree.fromstring(feed)
        for item in dom.xpath('//item'):
            for child in item.getchildren():  # did not find how to xpath content:encoded tag
                if child.tag.endswith("encoded"):
                    c = self._clean_content(
                        '<div class="blog-post">' + child.text + '</div>')
                    child.text = c  # "<![CDATA[" + c + "]]>"

        return etree.tostring(dom, encoding='unicode')

    def get_content(self, url: str, parameters: dict) -> str:
        page = requests.get(url=url, headers={})
        content = self._clean_content(page.text)
        return content

    def _clean_content(self, c):
        content = ""
        if not c is None:
            dom = etree.HTML(c)
            response.dom_utils.delete_xpaths(dom, [
                '//*[@class="permalink-pagination"]',
                '//*[@class="social-share"]',
                '//*[@class="post-author"]'
            ])

            objs = dom.xpath('//object')
            for obj in objs:
                if obj.attrib["data"].lower().endswith(".gif"):
                    src = obj.attrib["data"]
                    img = etree.Element("img")
                    img.set("src", src)
                    obj.getparent().getparent().getparent().getparent().append(img)

            response.dom_utils.delete_nodes(dom.xpath('//video'))

            content = response.dom_utils.get_content(
                dom, ['//div[contains(@class, "blog-post")]', '//div[contains(@class,"blog-post-content")]'])

            content = content.replace('<div class="blog-post">', '')
            content = content.replace('<div class="blog-post-content">', '')
            content = content.replace('</div>', '')
            content = re.sub(r'src="data:image[^"]*', '', content)
            content = content.replace("data-src", "style='height:100%;width:100%' src")
            content = re.sub(r'<!--(.*)-->', r"", content, flags=re.S)
        return content