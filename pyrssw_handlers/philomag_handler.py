from request.pyrssw_content import PyRSSWContent
import re
from typing import Dict

import requests
from lxml import etree

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import get_all_contents, text, to_string, xpath, get_content


class PhilomagHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.philomag.com">Philomag</a> website.

    Handler name: philomag

    Content:
        Get content of the page, removing paywall, menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "https://www.philomag.com/"

    def get_rss_url(self) -> str:
        return "https://www.philomag.com/rss-le-fil"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.philomag.com/sites/default/files/favicon_1.png"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        dom = etree.fromstring(feed.encode("utf-8"))

        for link in xpath(dom, "//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": text(link).strip()})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url)
        dom = etree.HTML(page.text, parser=None)

        seemore = xpath(dom, '//*[contains(@class, "see-more")]')
        if len(seemore) > 0:
            url = seemore[0].attrib["href"]
            if url.startswith("/"):
                url = self.get_original_website() + url[1:]
            page = session.get(url=url)
            dom = etree.HTML(page.text, parser=None)
        
        title = get_content(dom, ["//h1"])
        h1s = xpath(dom, "//h1")
        if len(h1s) > 0:
            h1s[0].getparent().remove(h1s[0])

        content, _ = get_all_contents(
            dom, ['//*[@id="adjustHeader"]', '//*[@id="block-philomag-content"]'])

        return PyRSSWContent(title + content, """
#philomag_handler .field--name-field-sur-titre {
    font-weight: 900;
    font-size: 1.1875rem;
    color: #1510de;
    margin-bottom: 15px;
}

#philomag_handler #wrapHeader {
    padding: 40px 15px 20px;
    text-align: center;
}

#philomag_handler #wrapHeader .wrap span {
    color: #707070;
    font-size: .8125rem;
}

#philomag_handler .blue {
    color: #1510de!important;
    display: inline-block;
}

#philomag_handler #wrapHeader .wrap .nb-words, body.node--type-dossier .node #wrapHeader .wrap .nb-words {
    margin-left: 15px;
    padding: 5px 5px 0;
    background-color: #a2a2a2;
    text-align: center;
    margin-right: 10px;
    white-space: nowrap;
}

#philomag_handler .d-none {
    display: none!important;
}

#philomag_handler .same-subject {
    margin-bottom: 30px;
    margin-top: 50px;
}

#philomag_handler .view h2:before {
    content: " ";
    width: 46px;
    height: 2px;
    margin-right: 20px;
    background-color: #1510de;
}

#philomag_handler .same-subject h2 {
    font-weight: 500;
    display: flex;
    margin-bottom: 10px;
    align-items: center;
    margin-left: 15px
}

#philomag_handler .node--view-mode-accroche-detail-magazine .tag-like {
    padding: 5px 5px 0;
    background-color: #a2a2a2;
    min-width: 80px;
    text-align: center;
    margin-right: 10px;
    display: inline-block;
}

#philomag_handler .col-12 {
    -webkit-box-flex: 0;
    -ms-flex: 0 0 100%;
    flex: 0 0 100%;
    max-width: 100%;
}

#philomag_handler #main-wrapper .field--type-image {
    margin-right: 0;
    float: unset;
    width: 100%;
}

#philomag_handler .col-4 {
    -webkit-box-flex: 0;
    -ms-flex: 0 0 33.33333%;
    flex: 0 0 33.33333%;
    max-width: 33.33333%;
}

#philomag_handler .node.node--type-article.node--view-mode-accroche-detail-magazine .content, .node.node--type-book.node--view-mode-accroche-detail-magazine .content, .node.node--type-dossier.node--view-mode-accroche-detail-magazine .content {
    margin: 15px 0 20px;
    display: -webkit-box;
    display: -ms-flexbox;
    display: flex;
    -webkit-box-orient: horizontal;
    -webkit-box-direction: normal;
    -ms-flex-flow: wrap row;
    flex-flow: wrap row;
    -webkit-box-pack: justify;
    -ms-flex-pack: justify;
    justify-content: space-between;
}

#philomag_handler .flex-grow {
    -webkit-box-flex: 5;
    -ms-flex-positive: 5;
    flex-grow: 5;
}

#philomag_handler #main-wrapper .field--type-image {
    margin-right: 0;
    float: unset;
    width: 100%;
}

""")
