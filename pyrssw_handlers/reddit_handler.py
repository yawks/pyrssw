import re
import unicodedata
import requests
from lxml import etree
from readability import Document
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

URL_REGEX = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

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
            if other != "":
                entry.xpath("./atom:content", namespaces=namespaces)[0].text = content.replace(thumb, other).replace("<td> &#32;","</tr><tr><td> &#32;")
            
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
        
        content: str = utils.dom_utils.get_all_contents(dom,
                                              ['//*[@data-test-id="post-content"]//h1',
                                               '//*[contains(@class,"media-element")]',
                                               '//*[@data-test-id="post-content"]//*[contains(@class,"RichTextJSON-root")]'])
        
        #case of posts with link(s) to external source(s) : we load the external content(s)
        external_link: str = utils.dom_utils.get_content(dom, ['//a[contains(@class,"styled-outbound-link")]'])
        if external_link != "":
            external_href = re.findall(r'href="([^"]*)"', external_link)
            for href in external_href:
                if self._is_external_content_url(href):
                    doc = Document(requests.get(href).text)
                    url_prefix = href[:len("https://")+len(href[len("https://"):].split("/")[0])+1]

                    content += "<hr/><p><u><a href=\"%s\">Source</a></u> : %s</p><hr/>" % (href, url_prefix)

                    content += self._get_content(doc)
                    #replace relative links
                    content = content.replace('href="/', 'href="' + url_prefix)
                    content = content.replace('src="/', 'src="' + url_prefix)
                    content = content.replace('href=\'/', 'href=\'' + url_prefix)
                    content = content.replace('src=\'/', 'src=\'' + url_prefix)
                    break

        content = content.replace("<video ", "<video controls ")
        return "<article>%s</article>" % content.replace("><", ">\n<")

    def _get_content(self, doc: Document) -> str:
        content: str = doc.summary()
        content = content.replace("<html>","").replace("</html>","").replace("<body>","").replace("</body>","")

        if content.find("\x92") > -1 or content.find("\x96") > -1 or content.find("\xa0") > -1:
            #fix enconding stuffs
            try:
                content = content.encode("latin1").decode("cp1252")
            except UnicodeEncodeError:
                pass

        return content

    def _is_external_content_url(self, href: str) -> bool:
        """Returns True if the href is a link to a website having content (not only a picture for example)

        Args:
            href (str): url

        Returns:
            bool: True if the href leads to real content
        """
        is_external_content_url: bool = False
        if re.match(URL_REGEX, href) and not (href.lower().endswith(".jpg") or href.lower().endswith(".png") or href.lower().endswith(".gif") or href.lower().endswith(".gifv")):
            is_external_content_url = True
        
        return is_external_content_url