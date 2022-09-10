import re
from typing import Dict, cast
from request.pyrssw_content import PyRSSWContent
import requests
from lxml import etree
from utils.dom_utils import delete_xpaths, get_first_node, to_string, xpath
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

        if parameters.get("page", "") == "journaux":
            content = session.get(url=self.get_rss_url() % "journaux").text
        else:
            content = session.get(url=self.get_rss_url() % "").text

        dom = etree.HTML(content)
        feed_xml = ""
        first_pubdate = ""

        for article in xpath(dom, '//main[@id="contents"]/article'):
            a = cast(etree._Element, get_first_node(article, [".//h1/a[last()]"]))
            title = a.text
            link = self.get_handler_url_with_parameters(
                {"url": self.get_original_website() + a.attrib.get("href", "")})
            guid = self.get_original_website() + a.attrib["href"]
            pubdate = cast(etree._Element, get_first_node(
                article, [".//time"])).attrib["datetime"]
            if first_pubdate == "":
                first_pubdate = pubdate

            img_node = cast(etree._Element, get_first_node(
                article, ['.//figure[@class="image"]//img']))
            img_url = ""
            if img_node is not None:
                src = cast(str, img_node.attrib["src"])
                if src.startswith("//"):
                    img_url = "https:" + src
                else:
                    img_url = self.get_original_website() + src
                    

            description = ""
            description_node = get_first_node(
                article, ['.//div[contains(@class,"entry-content")]'])
            if description_node is not None:
                description = to_string(
                    cast(etree._Element, description_node))

            feed_xml += f"""<item>
    <title>{title}</title>
    <link>{link}</link>
    <description><![CDATA[{description}]]></description>
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

        delete_xpaths(dom, ["//div[@class='formats']",
            "//p[@id='send-comment']",
            "//p[@id='follow-feed']"])

        content, _ = utils.dom_utils.get_all_contents(
            dom, [
                '//main[@id="contents"]',
            ])

        h2_comment_bgcolor = "#e9e6e4"
        a_comment_color = "#343434"
        if parameters.get("theme", "") == "dark":
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

#pyrssw_wrapper #comments ul {{
    list-style: none;
}}


#pyrssw_wrapper li.comment h2 a {{
    text-decoration: none;
    font-weight: bold;
    background-color: transparent;
    color: {a_comment_color}
}}

footer.actions {{
    font-size: 12px;
}}

code {{
    border: 1px solid #e9e6e4;
    border-radius: 4px;
    padding: 1px 4px;
    overflow-y: auto;
}}

code {{
    font-size: 0.8em;
    font-family: monospace;
}}

code, kbd, samp {{
    font-family: monospace, monospace;
    font-size: 1em;
}}

pre code {{
    display: block;
    margin: 10px 0 10px 10px;
    padding-left: 5px;
    padding-right: 0;
    border-width: 0 0 0 3px;
    border-color: #4c575f;
}}

#pyrssw_wrapper figure {{
    padding-right: 10px;
    padding-top: 10px;
}}

code .hll {{
  background-color: #ffffcc;
}}
code .c {{
  color: #888888;
}}
code .err {{
  color: #a61717;
  background-color: #e3d2d2;
}}
code .k {{
  color: #008800;
  font-weight: bold;
}}
code .cm {{
  color: #888888;
}}
code .cp {{
  color: #cc0000;
  font-weight: bold;
}}
code .c1 {{
  color: #888888;
}}
code .cs {{
  color: #cc0000;
  font-weight: bold;
  background-color: #fff0f0;
}}
code .gd {{
  color: #000000;
  background-color: #ffdddd;
}}
code .ge {{
  font-style: italic;
}}
code .gr {{
  color: #aa0000;
}}
code .gh {{
  color: #303030;
}}
code .gi {{
  color: #000000;
  background-color: #ddffdd;
}}
code .go {{
  color: #888888;
}}
code .gp {{
  color: #555555;
}}
code .gs {{
  font-weight: bold;
}}
code .gu {{
  color: #606060;
}}
code .gt {{
  color: #aa0000;
}}
code .kc {{
  color: #008800;
  font-weight: bold;
}}
code .kd {{
  color: #008800;
  font-weight: bold;
}}
code .kn {{
  color: #008800;
  font-weight: bold;
}}
code .kp {{
  color: #008800;
}}
code .kr {{
  color: #008800;
  font-weight: bold;
}}
code .kt {{
  color: #888888;
  font-weight: bold;
}}
code .m {{
  color: #0000dd;
  font-weight: bold;
}}
code .s {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .na {{
  color: #336699;
}}
code .nb {{
  color: #003388;
}}
code .nc {{
  color: #bb0066;
  font-weight: bold;
}}
code .no {{
  color: #003366;
  font-weight: bold;
}}
code .nd {{
  color: #555555;
}}
code .ne {{
  color: #bb0066;
  font-weight: bold;
}}
code .nf {{
  color: #0066bb;
  font-weight: bold;
}}
code .nl {{
  color: #336699;
  font-style: italic;
}}
code .nn {{
  color: #bb0066;
  font-weight: bold;
}}
code .py {{
  color: #336699;
  font-weight: bold;
}}
code .nt {{
  color: #bb0066;
  font-weight: bold;
}}
code .nv {{
  color: #336699;
}}
code .ow {{
  color: #008800;
}}
code .w {{
  color: #bbbbbb;
}}
code .mf {{
  color: #0000dd;
  font-weight: bold;
}}
code .mh {{
  color: #0000dd;
  font-weight: bold;
}}
code .mi {{
  color: #0000dd;
  font-weight: bold;
}}
code .mo {{
  color: #0000dd;
  font-weight: bold;
}}
code .sb {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .sc {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .sd {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .s2 {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .se {{
  color: #0044dd;
  background-color: #fff0f0;
}}
code .sh {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .si {{
  color: #3333bb;
  background-color: #fff0f0;
}}
code .sx {{
  color: #22bb22;
  background-color: #f0fff0;
}}
code .sr {{
  color: #008800;
  background-color: #fff0ff;
}}
code .s1 {{
  color: #dd2200;
  background-color: #fff0f0;
}}
code .ss {{
  color: #aa6600;
  background-color: #fff0f0;
}}
code .bp {{
  color: #003388;
}}
code .vc {{
  color: #336699;
}}
code .vg {{
  color: #dd7700;
}}
code .vi {{
  color: #3333bb;
}}
code .il {{
  color: #0000dd;
  font-weight: bold;
}}

.markItUp .code a {{
  background-image: url(https://linuxfr.org/images/markitup/page_white_code.png);
}}

""")
