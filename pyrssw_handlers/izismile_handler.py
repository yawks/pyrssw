import re
import urllib.parse as urlparse
from urllib.parse import parse_qs
import utils.dom_utils
from typing import Dict, List, Tuple, cast
import requests
import cloudscraper
from lxml import etree
import datetime
import time
from request.pyrssw_content import PyRSSWContent
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Content-Type": "text/html; charset=utf-8",
    "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
    "Cache-Control": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    "Pragma": "no-cache"
}

MAX_NB_PAGES = 11 # maximum number of pages to visit when crawling izismile website

class IzismileHandler(PyRSSWRequestHandler):

    def get_original_website(self) -> str:
        return "https://izismile.com/"

    def get_rss_url(self) -> str:
        return "https://feeds2.feedburner.com/izismile"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://izismile.com/favicon.ico"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers=HEADERS).text

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
            page = session.get(url=spicy_link, headers=HEADERS).text
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
        urls: List[str] = [url, "%s/page,1,%s" %
                           ("/".join(url.split("/")[:-1]), url.split("/")[-1])]
        nb_pages = 1
        content, url_next_page, comments, cpt_comments = self._get_content(
            url, session, with_title=True, cpt_comments=1)

        while url_next_page != "" and nb_pages <= MAX_NB_PAGES and url_next_page not in urls:
            urls.append(url_next_page)
            next_content, url_next_page, _, cpt_comments = self._get_content(
                url_next_page, session, with_title=False, cpt_comments=cpt_comments)
            content += next_content
            nb_pages += 1

        content += comments  # so far comments are the same on every page

        return PyRSSWContent(content, """
            #pyrssw_wrapper #izismile_handler div img {float:none; max-height: 90vh;margin: 0 auto; display: block; min-height:80px}
            #pyrssw_wrapper #izismile_handler img.avatar {
                float: left;
                margin-right: 15px;
                margin-bottom: 5px;
                display: block;
                max-width: 80px!important;
            }
            #pyrssw_wrapper #izismile_handler div .comm-inner img {
                min-height: auto;
                max-width: none;
                display: initial;
            }
            #pyrssw_wrapper #izismile_handler .comment-div {
                min-height: 90px;
            }
        """)

    def _get_content(self, url: str, session: requests.Session, with_title: bool = False, cpt_comments: int = 0) -> Tuple[str, str, str, int]:
        url_next_page = ""
        text = self._get_page_from_url(url, session)
        dom = etree.HTML(text)
        title = "" if not with_title else utils.dom_utils.get_content(dom, [
                                                                      "//h1"])
        comments = ""

        for a in dom.xpath("//a[contains(@href, \"https://izismile.com/outgoing.php\")]"):
            parsed = urlparse.urlparse(a.attrib["href"])
            if "url" in parse_qs(parsed.query):
                return "", parse_qs(parsed.query)["url"][0], "", cpt_comments

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
            '//*[contains(@class, "sordering")]',
            '//*[@id="dle-comments-form"]',
            '//*[@class="com_rate"]',
            '//*[@class="com_id"]',
            '//*[contains(@class,"com_buttons")]',
            '//*[contains(@class,"com_bots")]',
            '//div/center'])

        for script in dom.xpath('//script'):
            script.getparent().remove(script)

        pagers = dom.xpath('//*[@class="postpages"]')
        if len(pagers) > 1 and len(dom.xpath('//*[@class="postpages"]//a')) > 0:
            url_next_page = cast(str, dom.xpath(
                '//*[@class="postpages"]//a')[-1].values()[0])
        for pager in list(pagers):
            pager.getparent().remove(pager)

        pagers = dom.xpath('//*[@id="pagination-nums"]')
        for pager in pagers:
            pager.getparent().remove(pager)

        imgboxs = dom.xpath('//div[@class="imgbox"]')
        # replace <div class="imgbox"> by <p> tags
        cpt = cpt_comments
        for imgbox in imgboxs:
            imgbox.tag = "p"
            imgbox.attrib["id"] = str(cpt)
            cpt += 1
            del imgbox.attrib["class"]

        comments_nodes = dom.xpath('//*[@id="dlemasscomments"]')
        if len(comments_nodes) > 0:
            # isolate comments and then remove them from content
            comments = cast(str, etree.tostring(
                comments_nodes[0], encoding='unicode'))
            comments = comments.replace("src=\"data:", "_src=\"data:").replace(
                "data-src", "src")  # ugly hack
            comments = re.sub(r'(#\d+)', '<a href="\\1">\\1</a>', comments)
            utils.dom_utils.delete_xpaths(dom, ['//*[@id="dlemasscomments"]'])

        post_lists = dom.xpath('//*[@id="post-list"]')
        if len(post_lists) > 0:
            content = etree.tostring(
                post_lists[0], encoding='unicode')
        else:
            content = etree.tostring(dom, encoding='unicode')

        content = "%s%s" % (title, self._clean_content(content))

        return content, url_next_page, comments, cpt

    def _get_page_from_url(self, url, session: requests.Session) -> str:
        scraper = cloudscraper.create_scraper(delay=10, browser={
            'browser': 'firefox',
            'platform': 'windows',
            'mobile': False
        })
        text = scraper.get(url, verify=True).text
        
        if text.find("You do not have access to the site.") > -1:
            time.sleep(0.1)
            text = session.get(url=url, headers=HEADERS).text
        return text

    def _clean_content(self, c):
        content = c.replace("<div class=\"break\"/>", "")
        content = content.replace("<div class=\"tools\"/>", "")
        content = content.replace("<div class=\"clear\"/>", "")
        content = content.replace(" class=\"owl-carousel\"", "")
        content = content.replace("margin-bottom:30px;", "")
        content = re.sub(
            r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = content.replace('id="post-list"', 'id="mainbody"')

        content = content.replace('<div class="tools" style="display: none;"/>',
                                  '<div class="tools" style="display: block;"/>')
        content = re.sub(r'src="data:image/[^"]*"', '', content)
        #content = content.replace("data-src=", "src=")
        content = content.replace("data-poster=", "poster=")
        content = content.replace("class=\"lazyload\"", "")
        content = content.replace("Advertisement", "")
        content = content.replace("#0000ff", "#0099CC")
        return "<article>%s</article>" % content.replace("><", ">\n<")
