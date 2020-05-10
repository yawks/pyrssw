import re
import urllib.parse

import requests
from lxml import etree

import utils.dom_utils
from handlers.launcher_handler import USER_AGENT
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

URL_CONNECTION = "https://secure.lemonde.fr/sfuser/connexion"
URL_DECONNECTION = "https://secure.lemonde.fr/sfuser/deconnexion"


class LeMondeHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.lemonde.fr">Le Monde</a> website.

    Handler name: lemonde

    RSS parameters:
     - filter : international, politique, societe, les-decodeurs, sport, planete, sciences, campus, afrique, pixels, actualites-medias, sante, big-browser, disparitions, podcasts
       to invert filtering, prefix it with: ^
       eg :
         - /lemonde/rss?filter=politique            #only feeds about politique
         - /lemonde/rss?filter=politique,societe    #only feeds about politique and societe
         - /lemonde/rss?filter=^politique,societe   #all feeds but politique and societe
     - login : if you have an account you can use it to fetch full articles available only for subscribers
     - password : password of your account

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    @staticmethod
    def get_handler_name():
        return "lemonde"

    def get_original_website(self) -> str:
        return "https://www.lemonde.fr/"

    def get_rss_url(self) -> str:
        return "https://www.lemonde.fr/rss/une.xml"

    def get_feed(self, parameters: dict) -> str:
        feed = requests.get(url=self.get_rss_url(), headers={}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        link = '<link>'
        feed = feed.replace('<guid isPermaLink="false">', link)
        feed = feed.replace('<guid isPermaLink="true">', link)
        feed = feed.replace('</guid>', '</link>')
        feed = feed.replace(link, '<link>%s?%surl=' % (
            self.url_prefix, self._getAuthentificationSuffix(parameters)))

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)

        # available filters : international, politique, societe, les-decodeurs, sport, planete, sciences, campus, afrique, pixels, actualites-medias, sante, big-browser, disparitions, podcasts
        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "link[contains(text(), '/%s/')]", "not(link[contains(text(), '/%s/')])")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        feed = etree.tostring(dom, encoding='unicode')

        return feed

    def _getAuthentificationSuffix(self, parameters: dict):
        suffix = ""
        if "login" in parameters and "password" in parameters:
            suffix = "login=%s&amp;password=%s&amp;" % (
                urllib.parse.quote_plus(self.encrypt(parameters["login"])),
                urllib.parse.quote_plus(self.encrypt(parameters["password"])))

        return suffix

    def get_content(self, url: str, parameters: dict) -> str:
        session: requests.Session = self._authent(parameters)
        try:
            page = session.get(url=url, headers={"User-Agent": USER_AGENT})
            content = page.text

            dom = etree.HTML(content)

            utils.dom_utils.delete_xpaths(dom, [
                '//*[contains(@class, "meta__social")]',
                '//*[contains(@class, "breadcrumb")]',
                '//*[contains(@class, "article__reactions")]',
                '//*[contains(@class, "services")]',
                '//*[contains(@class, "article__footer-single")]',
                '//*[contains(@class, "wp-socializer")]',
                '//*[contains(@class, "insert")]',
                '//*[@id="comments"]',  # blog
                '//*[contains(@class, "post-navigation")]',  # blog
                '//*[contains(@class, "entry-footer")]',  # blog
                '//*[contains(@class, "catcher")]'  # tribune
            ])

            # le monde rss provides many sub websites with different html architecture
            content = utils.dom_utils.get_content(dom, [
                '//*[contains(@class, "zone--article")]',
                '//*[contains(@class, "article--content")]',  # tribune
                '//*[@id="post-container"]',
                '//*[@id="main"]'                               # blog
            ])

        except Exception as e:
            raise e
        finally:
            self._unauthent(session)

        return content

    def _authent(self, parameters: dict) -> requests.Session:
        session: requests.Session = requests.Session()
        page = session.get(url=URL_CONNECTION, headers={
                           "User-Agent": USER_AGENT})
        if "login" in parameters and "password" in parameters:
            idx = page.text.find("connection[_token]")
            if idx > -1:
                start = page.text[idx+len('connection[_token]" value="'):]
                token = start[0:start.find('"')]

                # credits to https://www.freecodecamp.org/news/how-i-scraped-7000-articles-from-a-newspaper-website-using-node-1309133a5070/
                data = {
                    "connection[mail]": parameters["login"],
                    "connection[password]": parameters["password"],
                    "connection[stay_connected]": "1",
                    "connection[save]": "",
                    "connection[newsletters]": "[]",
                    "connection[_token]": token}
                session.post(
                    url=URL_CONNECTION, data=data, headers=self._get_headers(URL_CONNECTION))

        return session

    def _get_headers(self, referer):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://secure.lemonde.fr/",
            "Host": "secure.lemonde.fr",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": USER_AGENT,
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": referer
        }
        return headers

    def _unauthent(self, session: requests.Session):
        session.get(url=URL_DECONNECTION, headers=self._get_headers("/"))
        session.close()
