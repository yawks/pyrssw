import re
import urllib.parse as urlparse
from urllib.parse import parse_qs
import utils.dom_utils

import requests
from lxml import etree

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
        feed = feed.replace('<link>', '<link>%s?url=' % self.url_prefix)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        content, url_next_page_2 = self._get_content(url, session)

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

        return content

    def _get_content(self, url, session: requests.Session):
        url_next_page = ""
        page = self._get_page_from_url(url, session)
        dom = etree.HTML(page.text)

        for a in dom.xpath("//a[contains(@href, \"https://izismile.com/outgoing.php\")]"):
            parsed = urlparse.urlparse(a.attrib["href"])
            if "url" in parse_qs(parsed.query):
                return "", parse_qs(parsed.query)["url"][0]

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "banners_btw_pics")]',
            '//*[contains(@class, "sordering")]'])

        for script in dom.xpath('//script'):
            script.getparent().remove(script)

        izi_videos = dom.xpath('//*[@class="daily_a" and text()=".mp4"]')
        for izi_video in izi_videos:
            parent = izi_video.getparent()

            video = etree.Element("video")
            video.set("controls", "")
            video.set("preload", "auto")
            video.set("poster", "")
            video.set("width", "100%")

            source = etree.Element("source")
            source.set("src", izi_video.attrib["href"])
            video.append(source)
            parent.getparent().append(video)

        pagers = dom.xpath('//*[@class="postpages"]')
        if len(pagers) > 2:
            url_next_page = dom.xpath(
                '//*[@class="postpages"]//a')[0].values()[0]
        for pager in list(pagers):
            pager.getparent().remove(pager)

        pagers = dom.xpath('//*[@id="pagination-nums"]')
        for pager in pagers:
            pager.getparent().remove(pager)

        post_lists = dom.xpath('//*[@id="post-list"]')

        if len(post_lists) > 0:
            content = etree.tostring(
                dom.xpath('//*[@id="post-list"]')[0], encoding='unicode')
        else:
            content = etree.tostring(dom, encoding='unicode')

        content = self._clean_content(content)

        return content, url_next_page

    def _get_page_from_url(self, url, session: requests.Session):
        page = session.get(url=url)
        if page.text.find("You do not have access to the site.") > -1:
            time.sleep(0.1)
            page = session.get(url=url, headers={
                'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'})
        return page

    def _clean_content(self, c):
        content = c.replace('<div class="break"/>', '')
        content = content.replace('<div class="tools"/>', '')
        content = re.sub(
            r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = re.sub(r'<div class="imgbox">(.*)</div>',
                         r"\1", content, flags=re.S)
        content = content.replace('id="post-list"', 'id="mainbody"')

        content = content.replace("<img", "<br/><br/><img")
        content = content.replace('<div class="tools" style="display: none;"/>',
                                  '<div class="tools" style="display: block;"/>')
        return content
