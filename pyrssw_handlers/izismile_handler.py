import re
import urllib.parse as urlparse
from urllib.parse import parse_qs
import utils.dom_utils
from typing import List
import requests
from lxml import etree
import datetime
import time
from request.pyrssw_content import PyRSSWContent
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class IzismileHandler(PyRSSWRequestHandler):

    @staticmethod
    def get_handler_name() -> str:
        return "izismile"

    def get_original_website(self) -> str:
        return "https://izismile.com/"

    def get_rss_url(self) -> str:
        return "https://feeds2.feedburner.com/izismile"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        # avoid php errors at the beginning when any
        feed = feed[feed.find("<"):]
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="false">', '<link>')  # NOSONAR
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')

        # spicy highlight links are index pages, we parse them and add new entries in the feed
        spicy_feeds: str = ""
        spicy_links: List[str] = re.findall(
            "<link>([^<]*izispicy[^<]*highlights[^<]*)</link>", str(feed))
        for spicy_link in spicy_links:
            page = session.get(url=spicy_link, headers={}).text
            dom = etree.HTML(page)
            for link in dom.xpath("//p/a[contains(@href, 'https://izispicy.com')]"):
                spans = link.xpath(".//span")
                title = "Izispicy"
                if len(spans) > 0:
                    title = spans[0].text
                spicy_feeds += """<item>
                        <title>%s</title>
                        <link>%s</link>
                        <description><![CDATA[%s]]></description>
                        <category>Izispicy</category>
                        <pubdate>%s</pubdate>
                    </item>""" % (title, link.attrib["href"], etree.tostring(link.getparent().getnext(), encoding='unicode'), datetime.datetime.now().strftime("%c"))
        feed = feed.replace("</channel>", spicy_feeds + "</channel>")

        feed = feed.replace('<link>', '<link>%s?url=' % self.url_prefix)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        content, url_next_page_2 = self._get_content(url, session, True)

        if url_next_page_2 != "":
            # add a page 2
            next_content, url_next_page_3 = self._get_content(
                url_next_page_2, session)
            content += next_content

            if url_next_page_3 != "" and url_next_page_2 != url_next_page_3 and url_next_page_3.find("page,1,") == -1:
                # add a page 3 (sometimes there is a redirection with an ongoing page)
                next_content, url_next_page_3 = self._get_content(
                    url_next_page_3, session)
                content += next_content

        return PyRSSWContent(content, """
            #pyrssw_wrapper #izismile_handler div img {float:none; min-width:400px}
        """)

    def _get_content(self, url, session: requests.Session, with_title:bool = False):
        url_next_page = ""
        page = self._get_page_from_url(url, session)
        dom = etree.HTML(page.text)
        title = "" if not with_title else utils.dom_utils.get_content(dom, ["//h1"])
        for a in dom.xpath("//a[contains(@href, \"https://izismile.com/outgoing.php\")]"):
            parsed = urlparse.urlparse(a.attrib["href"])
            if "url" in parse_qs(parsed.query):
                return "", parse_qs(parsed.query)["url"][0]

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "banners_btw_pics")]',
            '//*[@id="header"]',
            '//*[@id="footer"]',
            '//*[@id="browseby"]',
            '//*[@id="IZI_BTF_300c"]',
            '//*[contains(@class,"right_block")]',
            '//*[contains(@class,"help-comments-text")]',
            '//*[contains(@class,"paging")]',
            '//*[contains(@class,"like-list")]',
            '//*[contains(@class,"left_stat")]',
            '//*[contains(@class,"ajax-")]',
            '//*[contains(@class, "sordering")]'])

        for script in dom.xpath('//script'):
            script.getparent().remove(script)

        pagers = dom.xpath('//*[@class="postpages"]')
        if len(pagers) > 2:
            url_next_page = dom.xpath(
                '//*[@class="postpages"]//a')[0].values()[0]
        for pager in list(pagers):
            pager.getparent().remove(pager)

        pagers = dom.xpath('//*[@id="pagination-nums"]')
        for pager in pagers:
            pager.getparent().remove(pager)

        imgboxs = dom.xpath('//div[@class="imgbox"]')
        # replace <div class="imgbox"> by <p> tags
        for imgbox in imgboxs:
            imgbox.tag = "p"
            del imgbox.attrib["class"]

        post_lists = dom.xpath('//*[@id="post-list"]')
        if len(post_lists) > 0:
            content = etree.tostring(
                post_lists[0], encoding='unicode')
        else:
            content = etree.tostring(dom, encoding='unicode')

        content = "%s%s" %(title, self._clean_content(content))

        return content, url_next_page

    def _get_page_from_url(self, url, session: requests.Session):
        page = session.get(url=url)
        if page.text.find("You do not have access to the site.") > -1:
            time.sleep(0.1)
            page = session.get(url=url, headers={
                'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'})
        return page

    def _clean_content(self, c):
        content = c.replace("<div class=\"break\"/>", "")
        content = content.replace("<div class=\"tools\"/>", "")
        content = content.replace("<div class=\"clear\"/>", "")
        content = content.replace(" class=\"owl-carousel\"", "")
        content = content.replace("margin-bottom:30px;","")
        content = content.replace("<video", "<video preload=\"none\"")
        content = re.sub(
            r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = content.replace('id="post-list"', 'id="mainbody"')

        content = content.replace('<div class="tools" style="display: none;"/>',
                                  '<div class="tools" style="display: block;"/>')
        content = re.sub(r'src="data:image/[^"]*"', '', content)
        content = content.replace("data-src=", "src=")
        content = content.replace("data-poster=", "poster=")
        content = content.replace("class=\"lazyload\"", "")
        content = content.replace("Advertisement", "")
        content = content.replace("#0000ff", "#0099CC")
        return "<article>%s</article>" % content.replace("><", ">\n<")
