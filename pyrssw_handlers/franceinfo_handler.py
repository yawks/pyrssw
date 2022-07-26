import json
from request.pyrssw_content import PyRSSWContent
import re
from typing import Dict, Optional, cast

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import text, to_string, xpath


class FranceInfoHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.franceinfo.fr">France Info</a> website.

    Handler name: franceinfo

    RSS parameters:
     - filters : politique, faits-divers, societe, economie, monde, culture, sports, sante, environnement, ...

       to invert filtering, prefix it with: ^
       eg :
         - /franceinfo/rss?filter=politique            #only feeds about politique
         - /franceinfo/rss?filter=politique,societe    #only feeds about politique and societe
         - /franceinfo/rss?filter=^politique,societe   #all feeds but politique and societe

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    def get_original_website(self) -> str:
        return "http://www.franceinfo.fr/"

    def get_rss_url(self) -> str:
        return "http://www.franceinfo.fr/rss.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.francetvinfo.fr/skin/www/img/favicon/favicon.ico"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "link[contains(text(), '/%s/')]", "not(link[contains(text(), '/%s/')])")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        for link in xpath(dom, "//item/link"):
            link.text = self.get_handler_url_with_parameters(
                {"url": text(link).strip()})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url)
        content = page.text.replace(">", ">\n")

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace(
            "data-src", "style='height:100%;width:100%' src")
        dom = etree.HTML(content)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "block-share")]',
            '//*[@id="newsletter-onvousrepond"]',
            '//*[contains(@class, "partner-block")]',
            '//*[contains(@class, "a-lire-aussi")]',
            '//aside[contains(@class, "tags")]',
            '//*[contains(@class, "breadcrumb")]',
            '//*[contains(@class, "col-left")]',
            '//*[contains(@class, "col-right")]',
            '//*[contains(@class, "c-signature")]',
            '//*[contains(@class, "publication-date__modified")]',
            '//*[contains(@class, "social-aside")]',  # france3 regions
            '//*[contains(@class, "aside-img__content")]',  # france3 regions
            # france3 regions
            '//*[contains(@class, "social-button-content")]',
            '//*[contains(@class, "tags-button-content")]',  # france3 regions
            '//*[contains(@class, "article-share")]',  # france3 regions
            # france3 regions
            '//*[contains(@class, "article-share-fallback")]',
            # france3 regions
            '//*[contains(@class, "article-share-fallback")]',
            '//*[contains(@class, "related-content")]',
            '//*[contains(@class, "article__thematics")]',
            '//*[contains(@class, "article__related ")]',
            '//*[contains(@class, "subjects-title")]',
            '//*[contains(@class, "subjects-list")]',
            '//*[contains(@class, "audio-component")]',
            '//*[contains(@class, "social-zone")]',
            '//*[contains(@class, "c-signature__images")]',
            '//*[contains(@class, "article__share")]',
            '//*[contains(@class, "audio-player-container")]',
            '//*[contains(@class, "kamino-banner")]',
            '//*[@id="share-fallback"]', #francetvinfo
            '//*[contains(@class,"p-article__column--sidebar")]', #francetvinfo
            '//*[contains(@class,"o-related-cards")]', #francetvinfo
            '//*[contains(@class,"p-article__tags")]'  #francetvinfo
        ])

        _process_videos(dom)
        _process_pictures(dom)

        content = utils.dom_utils.get_content(
            dom, ['//div[contains(@class,"article-detail-block")]',
                  # francetvinfos
                  '//article[contains(@class,"page-content")]',
                  '//article[contains(@id,"node")]',  # france3 regions
                  '//main[contains(@role,"main")]', # france3 regions
                  '//main[contains(@class,"article")]',  # france3 regions
                  '//div[contains(@class,"article")]',  # france3 regions
                  '//article[contains(@class,"content-live")]',  # live
                  '//*[contains(@class, "article__column--left")]',  # la1ere
                  '//div[contains(@class, "content")]',
                  # sport.francetvinfo.fr
                  '//*[contains(@class,"article-detail-block")]'])

        if len(content.replace("\n", "").strip()) < 150:
            # less than 150 chars, we did not manage to get the content, use readability facility
            content = super().get_readable_content(session, url)

        # avoid loosing topCallImage because of remove script
        content = content.replace(
            "id=\"topCallImage\"", "id=\"topCallImage--\"")

        article_intro_start_idx = content.find("<p class=\"article__intro\">")
        if article_intro_start_idx > -1:
            article_intro_end_idx = content[article_intro_start_idx:].find(
                "</p>")
            content = content.replace("%s</p>" %
                                      content[article_intro_start_idx:article_intro_start_idx +
                                              article_intro_end_idx],
                                      "<h1>%s</h1>" % content[len("<p class=\"article__intro\">")+article_intro_start_idx:article_intro_start_idx+article_intro_end_idx])

        return PyRSSWContent(content, """
            #franceinfo_handler img.also-link__content__img {float:left;margin:0 10px 10px 0;}
            #franceinfo_handler ul li.localities__locality+li.localities__locality:before {padding: 8px;content: "/";}
            #franceinfo_handler ul li.localities__locality  {display: inline;font-size: 18px;}
            #franceinfo_handler .a-article__rubric {color: var(--blue-om,#007a99);font-size: 12px;line-height: 14px;text-decoration: none;font-size:16px; font-weight:500;}


        """)


def _process_videos(dom: etree._Element):
    json_contents = []
    for json_content in xpath(dom, '//script[@type="application/ld+json"]'):
        json_contents.append(json_content.text)
    if len(json_contents) > 0:
        for video in xpath(dom, '//figure[contains(@class,"francetv-player-wrapper")]'):
            for json_content in json_contents:
                if json_content.find('VideoObject') > -1:
                    js = json.loads(json_content, strict=False)
                    url = js.get("video", {}).get("embedUrl", "")
                    if url.strip() != "":
                        video.tag = "iframe"
                        video.attrib["src"] = url
                    break
    
def _process_pictures(dom: etree._Element):
    for picture in xpath(dom, "//picture"):
        noscripts = xpath(picture, ".//noscript")
        if len(noscripts) > 0:
            img = etree.fromstring(to_string(noscripts[0]).replace("<noscript>", "").replace("</noscript>", "").strip())
            picture.getparent().append(img)
            noscripts[0].getparent().remove(noscripts[0])
            picture.getparent().remove(picture)