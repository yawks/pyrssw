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


class LeMondeHandler(RequestHandler):
    def __init__(self, url_prefix):
        super().__init__(url_prefix, handler_name="lemonde",
                         original_website="https://www.lemonde.fr/", rss_url="https://www.lemonde.fr/rss/une.xml")

    def getFeed(self, parameters: dict):
        feed = requests.get(url=self.rss_url, headers={}).text
        feed = re.sub(r'<link>[^<]*</link>', '', feed)
        feed = feed.replace('<guid isPermaLink="false">', '<link>')
        feed = feed.replace('<guid isPermaLink="true">', '<link>')
        feed = feed.replace('</guid>', '</link>')
        feed = feed.replace('<link>', '<link>%s?%surl=' % (
            self.url_prefix, self._getAuthentificationSuffix(parameters)))

        # copy picture url from media to a img tag in description
        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        dom = lxml.etree.fromstring(feed)
        for item in dom.xpath("//item"):
            medias = item.xpath(".//*[@url!='']")
            descriptions = item.xpath(".//description")
            if len(medias) > 0 and len(descriptions) > 0:
                descriptions[0].text = '<img src="%s"/>%s' % (
                    medias[0].get('url'), descriptions[0].text)

        feed = lxml.etree.tostring(dom, encoding='unicode')

        return feed

    def _getAuthentificationSuffix(self, parameters: dict):
        suffix = ""
        if "login" in parameters and "password" in parameters:
            suffix = "login=%s&amp;password=%s&amp;" % (urllib.parse.quote_plus(
                parameters["login"]), urllib.parse.quote_plus(parameters["password"]))

        return suffix

    def getContent(self, url: str, parameters: dict):
        session: requests.Session = self._authent(parameters)
        try:
            page = session.get(url=url, headers=super().getUserAgent())
            content = page.text

            dom = lxml.etree.HTML(content)

            #deleteNodes(dom.xpath('//*[@class="meta meta__social   old__meta-social"]'))
            #deleteNodes(dom.xpath('//*[@class="breadcrumb "]'))

            c = response.dom_utils.getContent(
                dom, ['//*[@class="article__wrapper  "]', '//*[@id="post-container"]'])
            if c != "":
                content = "<p><a href='%s'>Source</a></p>%s" % (url, c)
                #content = content.replace("aria-hidden","dummy")
                #content = content.replace("data-format","dummy")

        except Exception as e:
            raise e
        finally:
            self._unauthent(session)

        return super().getWrappedHTMLContent(content, parameters)

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
