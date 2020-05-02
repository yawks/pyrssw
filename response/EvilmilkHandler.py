from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import re
import response.dom_utils


class EvilmilkHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="evilmilk",
                         original_website="https://www.evilmilk.com/", rss_url="https://www.evilmilk.com/rss.xml")

    def getFeed(self, parameters: dict):
        feed = requests.get(url=self.rss_url, headers={}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = re.sub(r'<link>', '<link>%s?url=' % self.url_prefix, feed)

        return self._replaceURLs(feed)

    def getContent(self, url: str, parameters: dict):
        page = requests.get(url=url, headers={})
        dom = lxml.etree.HTML(page.text)

        response.dom_utils.deleteNodes(dom.xpath('//*[@class="content-info"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@class="modal"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@class="comments text-center"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@id="undercomments"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@style="padding:10px"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@class="hrdash"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@class="row heading bottomnav"]'))
        response.dom_utils.deleteNodes(dom.xpath('//*[@id="picdumpnav"]'))

        main_bodies = dom.xpath('//*[@id="mainbody"]')
        if len(main_bodies) > 0:
            content = self._replaceURLs(lxml.etree.tostring(
                main_bodies[0], encoding='unicode'))
        else:
            content = self._replaceURLs(
                lxml.etree.tostring(dom, encoding='unicode'))
        content = self._cleanContent(content)

        #content = super()._replaceVideosByGifImages(lxml.etree.HTML(content))
        content = content.replace("<video ", "<video controls ")
        content = content.replace('autoplay=""', '')
        content = content.replace('playsinline=""', '')

        return super().getWrappedHTMLContent(content, parameters)

    def _cleanContent(self, c):
        content = c.replace('<div class="break"/>', '')
        content = content.replace('<div class="tools"/>', '')
        content = re.sub(
            r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = re.sub(r'<div class="imgbox">(.*)</div>',
                         r"\1", content, flags=re.S)
        return content

    def _replaceURLs(self, c):
        content = re.sub(
            r'href=(["\'])https://www.evilmilk.com/', r'href=\1' + self.url_prefix, c)
        content = re.sub(r'href=(["\'])/',
                         r'href=\1https://www.evilmilk.com/', content)
        content = re.sub(
            r'src=(["\'])/', r'src=\1https://www.evilmilk.com/', content)
        content = content.replace("<img", "<br/><br/><img")
        return content
