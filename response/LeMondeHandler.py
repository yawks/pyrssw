from response.RequestHandler import RequestHandler
import lxml.etree
import requests
import string
import re
import http.cookiejar
import urllib.parse
import response.dom_utils

URL_CONNECTION = "https://secure.lemonde.fr/sfuser/connexion"
URL_DECONNECTION = "https://secure.lemonde.fr/sfuser/deconnexion"


class PyRSSWRequestHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="lemonde",
                         original_website="https://www.lemonde.fr/", rss_url="https://www.lemonde.fr/rss/une.xml")

    def getFeed(self, parameters: dict) -> str:
        feed = requests.get(url=self.rss_url, headers={}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="false">', '<link>')
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = feed.replace('<link>', '<link>%s?%surl=' % (
            self.url_prefix, self._getAuthentificationSuffix(parameters)))

        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = lxml.etree.fromstring(feed)

        # available filters : international, politique, societe, les-decodeurs, sport, planete, sciences, campus, afrique, pixels, actualites-medias, sante, big-browser, disparitions, podcasts
        if "filter" in parameters:
            # filter only on passed category
            xpath_expression = response.dom_utils.getXpathExpressionForFilters(
                parameters, "link[contains(text(), '/%s/')]", "not(link[contains(text(), '/%s/')])")

            response.dom_utils.deleteNodes(dom.xpath(xpath_expression))

        feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    def _getAuthentificationSuffix(self, parameters: dict):
        suffix = ""
        if "login" in parameters and "password" in parameters:
            suffix = "login=%s&amp;password=%s&amp;" % (urllib.parse.quote_plus(
                parameters["login"]), urllib.parse.quote_plus(parameters["password"]))

        return suffix

    def getContent(self, url: str, parameters: dict) -> str:
        session: requests.Session = self._authent(parameters)
        try:
            page = session.get(url=url, headers=super().getUserAgent())
            content = page.text

            dom = lxml.etree.HTML(content)

            response.dom_utils.deleteNodes(
                dom.xpath('//*[contains(@class, "meta__social")]'))
            response.dom_utils.deleteNodes(
                dom.xpath('//*[contains(@class, "breadcrumb")]'))
            response.dom_utils.deleteNodes(
                dom.xpath('//*[contains(@class, "article__reactions")]'))
            response.dom_utils.deleteNodes(
                dom.xpath('//*[contains(@class, "services")]'))
            response.dom_utils.deleteNodes(
                dom.xpath('//*[contains(@class, "article__footer-single")]'))

            content = response.dom_utils.getContent(
                dom, ['//*[contains(@class, "zone--article")]', '//*[@id="post-container"]'])

        except Exception as e:
            raise e
        finally:
            self._unauthent(session)

        return content

    def _authent(self, parameters: dict) -> requests.Session:
        session = requests.Session()
        page = session.get(url=URL_CONNECTION, headers=super().getUserAgent())
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
                page = session.post(
                    url=URL_CONNECTION, data=data, headers=self._getHeaders(URL_CONNECTION))
            return session

    def _getHeaders(self, referer):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://secure.lemonde.fr/",
            "Host": "secure.lemonde.fr",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": super().getUserAgent()["User-Agent"],
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": referer
        }
        return headers

    def _unauthent(self, session: requests.Session):
        session.get(url=URL_DECONNECTION, headers=self._getHeaders("/"))
        session.close()
