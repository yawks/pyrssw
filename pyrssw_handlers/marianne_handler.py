from typing import Dict, cast
from request.pyrssw_content import PyRSSWContent
import re
from base64 import b64decode
import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import delete_xpaths, get_content, to_string, xpath


class Marianne(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.marianne.net">Marianne</a> website.

    Handler name: marianne

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_handler_name(self, parameters: Dict[str, str]):
        return "Marianne"

    def get_original_website(self) -> str:
        return "https://www.marianne.net/"

    def get_rss_url(self) -> str:
        return "https://www.marianne.net/rss.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://cdn.marianne.net/static/images/favicon/favicon.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        link = '<link>'
        feed = feed.replace('<guid isPermaLink="false">', link)
        feed = feed.replace('<guid isPermaLink="true">', link)
        feed = feed.replace('</guid>', '</link>')

        dom = etree.fromstring(feed.encode("utf-8"))
        for node in xpath(dom, "//link|//guid"):
            node.text = "%s" % self.get_handler_url_with_parameters(
                {"url": cast(str, node.text), "filter": parameters.get("filter", "")})
        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:

        page = session.get(url=url)
        content = page.text

        dom = etree.HTML(content)

        for premium_icon in xpath(dom, '//svg[contains(@class,"article__premium-icon")]'):
            # remove premium icons keeping tail content if any
            if premium_icon.tail is not None:
                if premium_icon.getparent().text is not None:
                    premium_icon.getparent().text += premium_icon.tail
                else:
                    premium_icon.getparent().text = premium_icon.tail
            premium_icon.getparent().remove(premium_icon)

        delete_xpaths(dom, [
            '//*[contains(@class,"share")]',
            '//*[contains(@class,"article__premium-button")]'
        ])

        headings = get_content(dom, ['//*[contains(@class,"article__headings")]'])
        delete_xpaths(dom, ['//*[contains(@class,"article__headings")]'])

        premium_article_content = ""
        article_bodies = xpath(dom, '//div[contains(@class,"article-body")]')
        if len(article_bodies) > 0 and "data-content-src" in article_bodies[0].attrib:
            premium_article_content += '<div class="article__content">%s</div>' % b64decode(
                article_bodies[0].attrib["data-content-src"].encode("utf8")).decode("utf8")
            utils.dom_utils.delete_xpaths(dom, [
                '//*[contains(@class, "article__content")]'
            ])

        symbols = get_content(dom, ['//svg']) #first svg contains symbols referenced later by xlinks
        content = symbols + headings + get_content(dom, [
            '//article[contains(@class,"article")]'
        ]) + premium_article_content

        bc_bg_color = "#ccc"
        bc_color = "#353535"
        bg_hover = "#aaa"
        if parameters.get("theme", "") == "dark":
            bc_bg_color = "#353535"
            bc_color = "#ccc"


        return PyRSSWContent(content, """

svg {
    display:none;
}

.breadcrumb {
    margin-left: -0.5rem;
    overflow: auto;
}

.article__item {
    margin: calc(var(--layout-gap)/2) 0;
}

.breadcrumb__item {
    display: flex;
    margin-left: 0.5rem;
}

.breadcrumb__label--link {
    transition: background-color .25s,color .25s;
}

.breadcrumb__label {
    flex: 0 0 auto;
    display: inline-block;
    padding: 8px;
    background-color: #BC_BG_COLOR#;
    color: #BC_COLOR#;
    border: 0.1rem solid var(--color-grey);
    font-family: var(--font-sans-serif-light);
    font-size: 16px;
    text-transform: uppercase;
    margin-top: 10px;
    margin-bottom: 10px;
}

.visually-hidden {
    position: absolute!important;
    height: 1px;
    width: 1px;
    overflow: hidden;
    clip: rect(1px,1px,1px,1px);
    white-space: nowrap;
}

.breadcrumb__icon {
    width: 1.5rem;
    height: 1.5rem;
}
.icon {
    display: block;
    margin: auto;
}

.breadcrumb__label--link:hover {
    background-color: #BG_HOVER#;
    color: #BC_BG_COLOR#;
}

.breadcrumb a, .breadcrumb a:active, .breadcrumb  a:focus, .breadcrumb  a:hover, .breadcrumb  a:visited {
    text-decoration: none;
}

.breadcrumb a {
    color: #BC_COLOR#!important;
}

figcaption {
    font-style: italic;
    font-size: 12px;
}

li {
    list-style: none;
}

@media (min-width: 75em)
.article-author__item {
    margin: 0 2rem;
}
.article-author__item {
    display: flex;
    align-items: center;
    margin: 0 1rem;
    padding: 1rem 0;
}

.link__decoration {
    position: relative;
}

        """.replace("#BC_BG_COLOR#", bc_bg_color).replace("#BC_COLOR#", bc_color).replace("#BG_HOVER#", bg_hover))
