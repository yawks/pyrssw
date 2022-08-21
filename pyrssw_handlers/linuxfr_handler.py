import re
from typing import Dict, cast
from request.pyrssw_content import PyRSSWContent
import requests
from lxml import etree
from utils.dom_utils import get_first_node, to_string, xpath
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class LinuxFRHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://linuxfr.org">Linux news</a> website.

    Handler name: linuxfr

    RSS parameters:
     - page : news, journaux


    Content:
        Get only content of the page + comments (remove menus, headers, footers, breadcrumb, ...)
    """

    def get_original_website(self) -> str:
        return "https://linuxfr.org"

    def get_rss_url(self) -> str:
        # we are not using provided atom stream, we will build one
        return "https://linuxfr.org/%s"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://linuxfr.org/favicon.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = ""
        if parameters.get("page", "") == "journaux":
            content = session.get(url=self.get_rss_url() % "journaux").text
        else:
            content = session.get(url=self.get_rss_url() % "").text

        dom = etree.HTML(content)
        feed_xml = ""
        first_pubdate = ""

        for article in xpath(dom, '//main[@id="contents"]/article'):
            a = cast(etree._Element, get_first_node(article, [".//h1/a[1]"]))
            title = a.text
            link = self.get_handler_url_with_parameters(
                {"url": self.get_original_website() + a.attrib.get("href", "")})
            guid = self.get_original_website() + a.attrib["href"]
            pubdate = cast(etree._Element, get_first_node(
                article, [".//time"])).attrib["datetime"]
            if first_pubdate == "":
                first_pubdate = pubdate

            img = cast(etree._Element, get_first_node(
                article, ['.//figure[@class="image"]//img']))
            img_url = self.get_original_website(
            ) + cast(str, img.attrib["src"])
            description = to_string(cast(etree._Element, get_first_node(
                article, ['.//div[contains(@class,"entry-content")]'])))

            feed_xml += f"""<item>
    <title>{title}</title>
    <link>{link}</link>
    <description>{description}</description>
    <pubDate>{pubdate}</pubDate>
    <enclosure url="{img_url}" length="50000" type="image/jpeg"/>
    <guid>{guid}</guid>
</item>
"""

        feed_xml = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>LinuxFr.org</title>
        <link>https://linuxfr.org</link>
        <language>fr</language>
        <pubDate>%s</pubDate>
        <image>
            <url>https://linuxfr.org/favicon.png</url>
            <title>LinuxFr.org</title>
            <link>https://linuxfr.org</link>
            <width>32</width>
            <height>32</height>
        </image>
        %s
    </channel>
</rss>
""" % (first_pubdate, feed_xml)

        return feed_xml

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url).text
        
        dom = etree.HTML(page)
        
        content, _ = utils.dom_utils.get_all_contents(
            dom, [
                '//main[@id="contents"]',
            ])

        h2_comment_bgcolor = "#e9e6e4"
        a_comment_color = "#343434"
        if parameters.get("dark", "") == "true":
            h2_comment_bgcolor = "#343434"
            a_comment_color = "#aaa9a8"
        
        return PyRSSWContent(content, f"""
article .image {{
    float: left;
    margin: 10px;
    margin-top: 10px;
}}
.tags ul {{
    display: inline;
}}
.tags ul li {{
    display: inline;
    padding: 0;
    list-style: none;
}}
article figure.score, article figure.datePourCss {{
    display: none;
}}
.content img {{
    width:100%!important;
}}

#comments img.avatar {{
    width:64px!important;
    height:auto;
    float:right;
    margin-right:0!important;
}}

li.comment>h2 {{
    font-size: 1.3em!important;
    margin-bottom: 0;
    margin-top: 10px;
    background: {h2_comment_bgcolor};
    clear: right;
    font-weight: bold;
}}

li.comment>p.meta {{
    margin-top: 0;
    margin-bottom: 3px;
    color: #93877b;
}}

li.comment>ul {{
    list-style: none;
}}

#pyrssw_wrapper li.comment h2 a {{
    text-decoration: none;
    font-weight: bold;
    background-color: transparent;
    color: {a_comment_color}
}}

""")