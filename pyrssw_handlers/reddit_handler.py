import re

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class RedditInfoHandler(PyRSSWRequestHandler):
    """Handler for sub reddits.

    Handler name: reddit

    RSS parameters:
      - subreddit : subreddit suffix, eg: france (which will be translated to: https://www.reddit.com/r/france/.rss)

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    @staticmethod
    def get_handler_name() -> str:
        return "reddit"

    def get_original_website(self) -> str:
        return "https://www.reddit.com/"

    def get_rss_url(self) -> str:
        return "https://www.reddit.com/.rss"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        rss_url: str = self.get_rss_url()
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}

        if "subreddit" in parameters:
            rss_url = "https://www.reddit.com/r/%s/.rss" % parameters["subreddit"]

        feed = session.get(url=rss_url, headers={}).text

        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        # I probably do not use etree as I should
        dom = etree.fromstring(feed)

        for entry in dom.xpath("//atom:entry", namespaces=namespaces):
            content = entry.xpath("./atom:content", namespaces=namespaces)[0].text

            #try to replace thumbnail with real picture
            imgs = re.findall(r'"http[^"]*jpg"', content)
            thumb:str = ""
            other:str= ""
            for img in imgs:
                if "thumbs.redditmedia" in img:
                    thumb = img
                else:
                    other = img
            entry.xpath("./atom:content", namespaces=namespaces)[0].text = content.replace(thumb, other)
            
            for link in entry.xpath("./atom:link", namespaces=namespaces):
                link.attrib["href"] = self.get_handler_url_with_parameters(
                    {"url": link.attrib["href"].strip()})

        feed = etree.tostring(dom, encoding='unicode')

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        cookie_obj = requests.cookies.create_cookie(
            domain="reddit.com", name="over18", value="1")
        session.cookies.set_cookie(cookie_obj)

        page = session.get(url=url)
        dom = etree.HTML(page.text)
        
        content = utils.dom_utils.get_all_contents(dom,
                                              ['//*[@data-test-id="post-content"]//h1',
                                               '//*[contains(@class,"media-element")]',
                                               '//*[@data-test-id="post-content"]//*[contains(@class,"RichTextJSON-root")]',
                                               '//*[@data-test-id="post-content"]//video'])

        return "<article>%s</article>" % content.replace("><", ">\n<")
