import re

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class FuturaSciencesHandler(PyRSSWRequestHandler):
    """Handler for french <a href="http://www.futura-sciences.com">Futura Sciences</a> website.

    Handler name: futurasciences

    RSS parameters:
     - filters :

       to invert filtering, prefix it with: ^
       eg :
         - /franceinfo/rss?filter=Etoiles              #only feeds about Etoiles
         - /franceinfo/rss?filter=Volcan,Etoiles       #only feeds about Volcan and Etoiles
         - /franceinfo/rss?filter=^Volcan,Etoiles      #all feeds but Volcan and Etoiles

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    @staticmethod
    def get_handler_name() -> str:
        return "futurasciences"

    def get_original_website(self) -> str:
        return "https://www.futura-sciences.com/"

    def get_rss_url(self) -> str:
        return "https://www.futura-sciences.com/rss/actualites.xml"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url()).text

        feed = re.sub(r'<guid>[^<]*</guid>', '', feed)
        feed = feed.replace('<link>', '<link>%s?url=' % (self.url_prefix))

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        feed = etree.tostring(dom, encoding='unicode')

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        page = session.get(url=url)
        content = page.text.replace(">", ">\n")

        content = re.sub(r'src="data:image[^"]*', '', content)
        content = content.replace(
            "data-src", "style='height:100%;width:100%' src")
        content = content.replace('data-fs-media', '')
        content = content.replace('class="fs-media"', '')
        dom = etree.HTML(content)

        # rework images
        imgs = dom.xpath('//img[contains(@class, "img-responsive")]')
        for img in imgs:
            new_img = etree.Element("img")
            new_img.set("src", img.attrib["src"])
            img.getparent().getparent().getparent().getparent().getparent().append(new_img)

        utils.dom_utils.delete_xpaths(dom, [
            '//*[contains(@class, "module-toretain")]',
            '//*[contains(@class, "image-module")]',
            '//*[contains(@class, "social-button")]'
        ])

        content = utils.dom_utils.get_content(
            dom, ['//div[contains(@class,"article-column")]'])

        return content
