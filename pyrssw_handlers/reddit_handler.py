import re
from typing import Optional
import requests
from lxml import etree
import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https://
    # domain...
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

IMGUR_GIFV = re.compile(r'(?:https?://.*imgur.com)(?:.*)/([^/]*).gifv')
PREVIEW_REDDIT = 'src="(https?://preview.redd.it/([^\?]*)[^"]*)"'

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
            content = entry.xpath(
                "./atom:content", namespaces=namespaces)[0].text

            # try to replace thumbnail with real picture
            imgs = re.findall(r'"http[^"]*jpg"', content)
            thumb: str = ""
            other: str = ""
            for img in imgs:
                if "thumbs.redditmedia" in img:
                    thumb = img
                else:
                    other = img
            if other != "":
                entry.xpath("./atom:content", namespaces=namespaces)[0].text = content.replace(
                    thumb, other).replace("<td> &#32;", "</tr><tr><td> &#32;")

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

        title: str = utils.dom_utils.get_all_contents(
            dom, ['//*[@data-test-id="post-content"]//h1'])
        content: str = utils.dom_utils.get_all_contents(dom,
                                                        ['//*[contains(@class,"media-element")]',
                                                         '//*[@data-test-id="post-content"]//*[contains(@class,"RichTextJSON-root")]'])

        # case of posts with link(s) to external source(s) : we load the external content(s)
        external_link: str = utils.dom_utils.get_content(
            dom, ['//a[contains(@class,"styled-outbound-link")]'])
        if external_link != "":
            external_hrefs = re.findall(r'href="([^"]*)"', external_link)
            for href in external_hrefs:
                if re.match(URL_REGEX, href):  # only valid urls
                    c: Optional[str] = self._manage_external_content(href)
                    if c is not None:
                        content += c
                        break

        content = self._manage_reddit_preview_images(content)
        content = content.replace("<video ", "<video controls ")
        return "<article>%s%s</article>" % (title, content.replace("><", ">\n<"))

    def _manage_external_content(self, href: str) -> Optional[str]:
        external_content: Optional[str] = None
        if not self._is_a_picture_link(href):
            external_content = super().get_readable_content(href, add_source_link=True)
        else:
            m = re.match(IMGUR_GIFV, href)
            if m is not None:
                imgur_id: str = m.group(1)
                external_content = """<video poster="//i.imgur.com/%s.jpg" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" style="width: 480px; height: 854px;">
                        <source src="//i.imgur.com/%s.mp4" type="video/mp4">
                    </video>""" % (imgur_id, imgur_id)
            else:
                external_content = "<img src=\"%s\"/>" % href

        return external_content


    def _manage_reddit_preview_images(self, content) -> str:
        """Use directly the image instead of the preview

        Args:
            content ([type]): html content

        Returns:
            str: the content where preview images have been replaced by target
        """
        content_without_preview: str = content
        previews = re.findall(PREVIEW_REDDIT, content)
        for preview in previews:
            content_without_preview = content.replace(preview[0], "https://i.redd.it/%s" % preview[1])
        
        return content_without_preview

    def _is_a_picture_link(self, href: str) -> bool:
        """Returns True if the href is a link to a picture

        Args:
            href (str): url

        Returns:
            bool: True if the href leads to real content
        """
        _is_a_picture_link: bool = False
        if href.lower().endswith(".jpg") or href.lower().endswith(".png") or href.lower().endswith(".gif") or href.lower().endswith(".gifv"):
            _is_a_picture_link = True

        return _is_a_picture_link
