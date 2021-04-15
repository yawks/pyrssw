import json
import html
from request.pyrssw_content import PyRSSWContent
from utils.url_utils import is_a_picture_url, is_url_valid
from handlers.feed_type.atom_arranger import NAMESPACES
import re
from typing import Dict, List, Optional, cast
from requests import cookies, Session
from lxml import etree
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from utils.dom_utils import get_content, to_string, xpath, get_first_node
from utils.json_utils import get_node, get_node_value_if_exists

NAMESPACES = {'atom': 'http://www.w3.org/2005/Atom'}

IMGUR_GIFV = re.compile(r'(?:https?://.*imgur.com)(?:.*)/([^/]*).gifv')
IMG_PREVIEW_REDDIT = 'src="(https?://preview.redd.it/([^\?]*)[^"]*)"'


class RedditHandler(PyRSSWRequestHandler):
    """Handler for reddit.

    Handler name: redditng

    RSS parameters:
      - sub : sub suffix, eg: france (which will be translated to: https://www.reddit.com/r/france/.rss)

    Content:
        Get content of the page, removing menus, headers, footers, breadcrumb, social media sharing, ...
    """

    @staticmethod
    def get_handler_name() -> str:
        return "redditng"

    def get_original_website(self) -> str:
        return "https://www.reddit.com/"

    def get_rss_url(self) -> str:
        return "https://www.reddit.com/.rss"

    def get_feed(self, parameters: dict, session: Session) -> str:
        rss_url: str = self.get_rss_url()

        if "sub" in parameters:
            rss_url = "https://www.reddit.com/r/%s/.rss" % parameters["sub"]

        feed = session.get(url=rss_url, headers={}).text

        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        # I probably do not use etree as I should
        dom = etree.fromstring(feed)

        for entry in xpath(dom, "//atom:entry", namespaces=NAMESPACES):
            content = cast(str, xpath(entry, "./atom:content",
                                      namespaces=NAMESPACES)[0].text)

            # try to replace thumbnail with real picture
            imgs = re.findall(r'"http[^"]*jpg"', content)
            thumb: str = ""
            other: str = ""
            for img in imgs:
                if "thumbs.redditmedia" in img:
                    thumb = img
                else:
                    other = img
            if thumb != "" and other != "":
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

        return self.get_reddit_content(url, session, True)

    def get_reddit_content(self, url: str, session: Session, with_comments: bool) -> PyRSSWContent:
        content: str = ""
        json_content = session.get(url="%s/.json" % url, headers=self._get_headers()).content
        root = json.loads(json_content)
        datatypes = self._get_datatypes_json(root, "t3")  # t3 : content
        for data in datatypes:
            content += "<h1>%s</h1>" % get_node_value_if_exists(
                data, "title")
            self_html: str = get_node_value_if_exists(data, "selftext_html")
            post_hint: str = get_node_value_if_exists(data, "post_hint")
            removed_by: str = get_node_value_if_exists(
                data, "removed_by") + get_node_value_if_exists(data, "removed_by_category")
            if removed_by == "":
                url_overridden_by_dest: str = get_node_value_if_exists(
                    data, "url_overridden_by_dest")
                if len(url_overridden_by_dest) > 0 and url_overridden_by_dest[:1] == '/':
                    url_overridden_by_dest = "https://www.reddit.com" + url_overridden_by_dest
                preview_image: Optional[str] = cast(
                    Optional[str], get_node(data, "preview", "images", 0, "source", "url"))
                is_gallery: str = str(
                    get_node_value_if_exists(data, "is_gallery"))
                domain: Optional[str] = cast(str, get_node(data, "domain"))

                if self_html != "":
                    content += html.unescape(self_html)

                if is_gallery == "True":
                    content += self._manage_gallery(data)

                c: Optional[str] = self._manage_external_content(session,
                                                                 url_overridden_by_dest, post_hint, preview_image, domain, data)
                if c is not None:
                    content += c

                content = self._manage_reddit_preview_images(content)
                content = content.replace("<video ", "<video controls ")
            else:
                content = "Content removed"

        comments: str = ""
        if with_comments:
            comments = "<hr/><h2>Comments</h2>"
            comments_json = self._get_datatypes_json(
                root, "t1")  # t1 : comments
            for comment_json in comments_json:
                comments += self.get_comments(comment_json)

        content = "<article>%s%s</article>" % (
            content, comments)

        return PyRSSWContent(content)

    def _manage_reddit_preview_images(self, content) -> str:
        """Use directly the image instead of the preview

        Args:
            content ([type]): html content

        Returns:
            str: the content where preview images have been replaced by target
        """
        content_without_preview: str = content
        img_previews = re.findall(IMG_PREVIEW_REDDIT, content)
        for preview in img_previews:
            content_without_preview = content.replace(
                preview[0], "https://i.redd.it/%s" % preview[1])

        dom = etree.HTML(content_without_preview)
        for a in xpath(dom, "//a"):
            if "href" in a.attrib and a.attrib["href"].find("://preview.redd.it/") > -1:
                img = etree.Element("img")
                img.set("src", a.attrib["href"].replace(
                    "preview.redd.it", "i.redd.it"))
                a.getparent().append(img)
                a.getparent().remove(a)

        content_without_preview = to_string(dom)

        return content_without_preview

    def _get_datatypes_json(self, data: dict, ttype: str) -> List[dict]:
        datatype_json: List[dict] = []
        if len(data) > 0:
            for d in data:
                nodes = get_node(d, "data", "children")
                if nodes is not None:
                    for node in nodes:
                        if "kind" in node and node["kind"] == ttype and "data" in node:
                            datatype_json.append(node["data"])

        return datatype_json

    def _manage_external_content(self, session: Session, href: Optional[str], post_hint: str, preview_image: Optional[str], domain: str, data: dict) -> Optional[str]:
        external_content: Optional[str] = None
        if is_url_valid(href):
            url: str = cast(str, href)
            external_content = self._get_content_by_url(
                session, url, post_hint)
            if external_content is None or external_content == "":
                external_content = self._get_content_by_post_hint(
                    session, url, post_hint, preview_image, domain, data)
                if external_content is None:
                    external_content = "<p>UNKOWN post_hint '%s'</p>" % post_hint

        return external_content

    def _get_content_by_url(self, session: Session, url: str, post_hint: str) -> Optional[str]:
        external_content: Optional[str] = None
        if url.startswith("https://twitter.com/"):
            external_content = "<p><a href=\"%s\">Tweet</a></p>" % url
        elif url.startswith("https://www.youtube.com/"):
            external_content = "<iframe class=\"pyrssw_youtube\" src=\"%s\">Youtube</iframe></p>" % url.replace(
                "watch?v=", "embed/")
        elif is_a_picture_url(url):
            external_content = "<img src=\"%s\"/>" % url
        elif url.find("imgur.com/") > -1:
            external_content = self._manage_imgur(session, url)
        elif url.find("gifs.com/") > -1:
            page = session.get(url)
            dom = etree.HTML(page.text)
            external_content = get_content(dom, ["//video"])
        elif (url.find("://v.redd.it/") > -1 or url.find("://www.reddit.com/") > -1) and post_hint in ["link", ""]:
            r = session.get(url)
            external_content = self.get_reddit_content(
                r.url, session, False).content
        else:
            m = re.match(IMGUR_GIFV, url)
            if m is not None:
                imgur_id: str = m.group(1)
                external_content = """<p><video poster="//i.imgur.com/%s.jpg" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" >
                        <source src="//i.imgur.com/%s.mp4" type="video/mp4">
                    </video></p>""" % (imgur_id, imgur_id)

        return external_content

    def _get_content_by_post_hint(self, session: Session, url: str, post_hint: str, preview_image: Optional[str], domain: str, data: dict) -> Optional[str]:
        external_content: Optional[str] = None
        if post_hint == "rich:video":
            external_content = "<p><img src=\"%s\"/></p><p><a href=\"%s\">Source : %s</a></p>" % (
                preview_image, url, domain)
        elif post_hint == "hosted:video":
            video_url = get_node(
                data, "media", "reddit_video", "hls_url")
            external_content = """<p><video poster="%s" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" >
                        <source src="%s" type="application/vnd.apple.mpegURL">
                    </video></p>""" % (preview_image, video_url)
        elif post_hint == "image" or is_a_picture_url(url):
            external_content = "<p><img src=\"%s\"/></p>" % url
        elif post_hint in ["", "link"]:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Content-Type": "text/html; charset=utf-8",
                "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
                "Cache-Control": "no-cache",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
                "Pragma": "no-cache",
                "Referer": "https://www.reddit.com/"
            }
            external_content = super().get_readable_content(
                session, url, headers=headers,  add_source_link=True)

        return external_content

    def _manage_imgur(self, session: Session, url: str) -> str:
        external_content: str = ""

        page = session.get(url)
        dom = etree.HTML(page.text)
        img = get_first_node(dom, ['//meta[@property="og:image"]/@content'])
        video = get_first_node(dom, ['//meta[@property="og:video"]/@content'])
        if img is not None:
            if video is not None:
                external_content = """<p><video poster="%s" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" >
                        <source src="%s">
                    </video></p>""" % (img, video)
            else:
                external_content = "<img src=\"%s\"/>" % img

        return external_content

    def get_comments(self, comments: dict, deep: int = 0) -> str:
        """Append comments to the content. The webscrapped version contains only 2 levels in threads.
        The comments are displayed in a <ul> list. Only the comment, no nickname, no points, no date.

        Args:
            comments (dict): json containing comments

        Returns:
            str: html content for comments
        """

        comments_html: str = ""
        if deep < 3:  # not to deep
            if "body_html" in comments:
                comments_html += "<li>%s</li>" % html.unescape(
                    comments["body_html"])

            replies = get_node(comments, "replies", "data", "children")
            if isinstance(replies, list):
                for reply in replies:
                    if "kind" in reply and reply["kind"] == "t1" and "data" in reply:
                        comments_html += self.get_comments(
                            reply["data"], deep+1)

            comments_html = "<ul>%s</ul>" % comments_html

        return comments_html

    def _manage_gallery(self, post: dict) -> str:
        gallery_html: str = ""
        images: Dict[str, str] = self._get_gallery_images(post)

        if "gallery_data" in post and post["gallery_data"] is not None and "items" in post["gallery_data"]:
            for item in post["gallery_data"]["items"]:
                if "caption" in item:
                    if "outbound_url" in item:
                        gallery_html += "<p><a href=\"%s\">%s</a></p>" % (
                            item["outbound_url"], item["caption"])
                    else:
                        gallery_html += "<p>%s</p>" % item["caption"]

                if item["media_id"] in images:
                    gallery_html += images[item["media_id"]]

        return gallery_html

    def _get_gallery_images(self, post: dict) -> Dict[str, str]:
        images: Dict[str, str] = {}

        if "media_metadata" in post:
            for node_name in post["media_metadata"]:
                node = post["media_metadata"][node_name]
                if "e" in node and node["e"] == "Image" and "p" in node and len(node["p"]) > 0:
                    images[node["id"]] = "<p><img src=\"%s\"/>" % node["p"][-1]["u"]

        return images

    def _get_headers(self):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0",
            "Connection": "keep-alive",
            "Pragma": "no-cache"
        }