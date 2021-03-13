from request.pyrssw_content import PyRSSWContent
from utils.url_utils import is_url_valid
from handlers.feed_type.atom_arranger import NAMESPACES
import re
from typing import Optional, Tuple, cast
from requests import cookies, Session
from lxml import etree
import utils.dom_utils
from urllib.parse import urlparse
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import get_content, to_string, xpath

NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}

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

    def get_feed(self, parameters: dict, session: Session) -> str:
        rss_url: str = self.get_rss_url()

        if "subreddit" in parameters:
            rss_url = "https://www.reddit.com/r/%s/.rss" % parameters["subreddit"]

        feed = session.get(url=rss_url, headers={}).text

        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        # I probably do not use etree as I should
        dom = etree.fromstring(feed)

        for entry in xpath(dom, "//atom:entry", namespaces=NAMESPACES):
            content = cast(str, xpath(entry, "./atom:content", namespaces=NAMESPACES)[0].text)

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
                xpath(entry, "./atom:content", namespaces=NAMESPACES)[0].text = content.replace(
                    thumb, other).replace("<td> &#32;", "</tr><tr><td> &#32;")

            for link in xpath(entry, "./atom:link", namespaces=NAMESPACES):
                link.attrib["href"] = self.get_handler_url_with_parameters(
                    {"url": cast(str, link.attrib["href"].strip())})

        feed = to_string(dom)

        return feed

    def get_content(self, url: str, parameters: dict, session: Session) -> PyRSSWContent:
        cookie_obj = cookies.create_cookie(
            domain="reddit.com", name="over18", value="1")
        session.cookies.set_cookie(cookie_obj)

        page = session.get(url=url)
        dom = etree.HTML(page.text)

        alt: str = ""
        title: str = ""

        title, alt = utils.dom_utils.get_all_contents(
            dom, ['//*[@data-test-id="post-content"]//h1'])
        content, alt = utils.dom_utils.get_all_contents(dom,
                                                        ['//*[contains(@class,"media-element")]',
                                                         '//*[contains(@data-click-id,"media")]//video',
                                                         '//*[@data-test-id="post-content"]//*[contains(@class,"RichTextJSON-root")]'], alt_to_p=True)

        content += self._get_figures(dom)
        # case of posts with link(s) to external source(s) : we load the external content(s)
        external_link: str = utils.dom_utils.get_content(
            dom, ['//a[contains(@class,"styled-outbound-link")]'])
        if external_link != "":
            external_hrefs = re.findall(r'href="([^"]*)"', external_link)
            for href in external_hrefs:
                if is_url_valid(href):
                    c: Optional[str] = self._manage_external_content(session, href)
                    if c is not None:
                        content = c
                        break

        content = self._manage_reddit_preview_images(content)
        content = content.replace("<video ", "<video controls ")
        if len(alt.strip()) > 0:
            content += "<p>%s</p>" % alt
        content = "<article>%s%s%s</article>" % (
            title, content, self.get_comments(dom))

        return PyRSSWContent(content)

    def _get_figures(self, dom: etree._Element) -> str:
        """Extract pictures in figure lists (ie multi images in /r/comics)

        Args:
            dom (etree._Element): root node of the page

        Returns:
            str: html content
        """
        content: str = ""
        for node in xpath(dom, '//*[@data-test-id="post-content"]//ul/li/figure/a'):
            if "href" in node.attrib:
                content += "<p><img src=\"%s\"/></p>" % node.attrib["href"]
        return content
    
    def _manage_external_content(self, session: Session, href: str) -> Optional[str]:
        external_content: Optional[str] = None
        if not self._is_a_picture_link(href):
                external_content = super().get_readable_content(session, href, add_source_link=True)
        else:
            m = re.match(IMGUR_GIFV, href)
            if m is not None:
                imgur_id: str = m.group(1)
                external_content = """<p><video poster="//i.imgur.com/%s.jpg" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" style="width: 480px; height: 854px;">
                        <source src="//i.imgur.com/%s.mp4" type="video/mp4">
                    </video></p>""" % (imgur_id, imgur_id)
            else:
                external_content = "<p><img src=\"%s\"/></p>" % href

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
            content_without_preview = content.replace(
                preview[0], "https://i.redd.it/%s" % preview[1])

        return content_without_preview

    def _is_a_picture_link(self, href: str) -> bool:
        """Returns True if the href is a link to a picture

        Args:
            href (str): url

        Returns:
            bool: True if the href leads to real content
        """
        _is_a_picture_link: bool = False
        parsed_url = urlparse(href)
        for extension in [".jpg", ".jpeg", ".png", ".gif", ".gifv"]:
            if parsed_url.path.lower().endswith(extension):
                _is_a_picture_link = True
                break

        return _is_a_picture_link

    def get_comments(self, dom: etree) -> str:
        """Append comments to the content. The webscrapped version contains only 2 levels in threads.
        The comments are displayed in a <ul> list. Only the comment, no nickname, no points, no date.

        Args:
            dom (etree): sub reddit content parsed

        Returns:
            str: html content for comments
        """
        intro: str = "<hr/><h2>Comments</h2>"
        last_level: str = "level 1"
        comments: str = "<ul>"
        for entry in dom.xpath("//*[@data-test-id=\"comment\"]", namespaces=NAMESPACES):
            c, last_level = self._manage_comment_level(last_level, entry)
            comments += c

            comments += "<li>"
            ps = entry.xpath(".//p")
            for p in ps:
                if "class" in p.attrib:
                    del p.attrib["class"]
                comments += to_string(p)

            comments += "</li>"

        comments += "</ul>"

        if comments == "<ul></ul>":
            comments = "<p>No comment so far!</p>"

        return intro + comments

    def _manage_comment_level(self, level: str, entry: etree._Element) -> Tuple[str, str]:
        ul_tag: str = ""
        last_level: str = level
        spans = xpath(cast(etree._Element, entry.getparent()),
                      ".//span[contains(./text(),'level ')]")
        for span in spans:
            if span.text != level:
                last_level = cast(str, span.text)
                if span.text == "level 2":
                    ul_tag = "<ul>"
                else:
                    ul_tag = "</ul>"
        return ul_tag, last_level
