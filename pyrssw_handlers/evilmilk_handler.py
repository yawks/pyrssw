import re
from typing import cast
import requests
from lxml import etree
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler


class EvilmilkHandler(PyRSSWRequestHandler):

    @staticmethod
    def get_handler_name() -> str:
        return "evilmilk"

    def get_original_website(self) -> str:
        return "https://www.evilmilk.com/"

    def get_rss_url(self) -> str:
        return "https://www.evilmilk.com/rss.xml"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = re.sub(r'<link>', '<link>%s?url=' % self.url_prefix, feed)

        return self._replace_urls(feed)

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        page = session.get(url=url, headers={})
        dom = etree.HTML(page.text)

        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="content-info"]'))
        utils.dom_utils.delete_nodes(dom.xpath('//*[@class="modal"]'))
        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="comments text-center"]'))
        utils.dom_utils.delete_nodes(dom.xpath('//*[@id="undercomments"]'))
        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@style="padding:10px"]'))
        utils.dom_utils.delete_nodes(dom.xpath('//*[@class="hrdash"]'))
        utils.dom_utils.delete_nodes(
            dom.xpath('//*[@class="row heading bottomnav"]'))
        utils.dom_utils.delete_nodes(dom.xpath('//*[@id="picdumpnav"]'))

        main_bodies = dom.xpath('//*[@id="mainbody"]')
        if len(main_bodies) > 0:
            content = self._replace_urls(etree.tostring(
                main_bodies[0], encoding='unicode'))
        else:
            content = self._replace_urls(
                etree.tostring(dom, encoding='unicode'))
        content = self._clean_content(content)

        content = content.replace("<video ", "<video width=\"100%\" controls ")
        content = content.replace('autoplay=""', '')
        content = content.replace('playsinline=""', '')
        content = re.sub(r'poster=(["\'])/',
                         r'poster=\1https://www.evilmilk.com/', content)

        return content

    def _clean_content(self, c):
        content = c.replace('<div class="break"/>', '')
        content = content.replace('<div class="tools"/>', '')
        content = re.sub(
            r'<span class="sordering"><a class="back" href="#[^"]*"/><a name="[^"]*">[^<]*</a><a class="next" href="#[^"]*"/></span>', '', content)
        content = re.sub(r'<div class="imgbox">(.*)</div>',
                         r"\1", content, flags=re.S)
        return content

    def _replace_urls(self, c):
        content = re.sub(
            r'href=(["\'])https://www.evilmilk.com/', r'href=\1' + cast(str, self.url_prefix), c)
        content = re.sub(r'href=(["\'])/',
                         r'href=\1https://www.evilmilk.com/', content)
        content = re.sub(
            r'src=(["\'])/', r'src=\1https://www.evilmilk.com/', content)
        content = content.replace("<img", "<br/><br/><img")
        return content
