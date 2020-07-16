import re
import traceback
import urllib.parse as urlparse
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote_plus, unquote_plus
import html
import requests
from cryptography.fernet import Fernet, InvalidToken
from lxml import etree
from typing_extensions import Type

from handlers.request_handler import RequestHandler
from pyrssw_handlers.abstract_pyrssw_request_handler import (
    ENCRYPTED_PREFIX, PyRSSWRequestHandler)
from storage.article_store import ArticleStore
from storage.session_store import SessionStore

HTML_CONTENT_TYPE = "text/html; charset=utf-8"
FEED_XML_CONTENT_TYPE = "text/xml; charset=utf-8"

# duration in minutes of a session
SESSION_DURATION = 30 * 60

# TODO: code cleaning => create classes for feed and content handling


class LauncherHandler(RequestHandler):
    """Handler which launches custom PyRSSWRequestHandler"""

    def __init__(self, module_name: str,
                 handlers: List[Type[PyRSSWRequestHandler]],
                 serving_url_prefix: Optional[str],
                 url: str,
                 crypto_key: bytes,
                 session_id: str, source_ip: Optional[str]):
        super().__init__(source_ip)
        self.handler: Optional[PyRSSWRequestHandler] = None
        self.serving_url_prefix: Optional[str] = serving_url_prefix
        self.handler_url_prefix: str = "%s/%s" % (
            serving_url_prefix, module_name)
        self.url: str = url
        self.module_name: str = module_name
        self.fernet: Fernet = Fernet(crypto_key)
        self.session_id: str = session_id
        for h in handlers:  # find handler from module_name
            if h.get_handler_name() == module_name:
                self.handler = h(self.fernet, self.handler_url_prefix)
                break

        if self.handler is not None:
            self.process()
        else:
            raise Exception("No handler found for name '%s'" % module_name)

    def process(self):
        """process the url"""
        try:
            path, parameters = self._extract_path_and_parameters(self.url)
            if path.find("/rss") == 0:
                self._process_rss(parameters)
            else:
                self._process_content(self.url, parameters)

            self.set_status(200)

        except Exception as e:
            self.contents = """<html>
                                    <body>
                                        %s
                                        <br/>
                                        %s
                                        <br/>
                                        <pre>%s</pre>
                                    </body>
                                </html>""" % (self.url, str(e), traceback.format_exc())
            self.content_type = "text/html; utf-8"
            self.set_status(500)

    def _process_content(self, url, parameters):
        self._log("content page requested: %s" % unquote_plus(url))
        requested_url = url
        self.content_type = HTML_CONTENT_TYPE
        session: requests.Session = SessionStore.instance().get_session(self.session_id)

        if "url" in parameters:
            requested_url = parameters["url"]
        if not requested_url.startswith("https://") and not requested_url.startswith("http://"):
            requested_url += self.handler.get_original_website()

        if "plain" in parameters and parameters["plain"] == "true":
            # return the requested page without any modification
            self.contents = session.get(requested_url).text
        else:
            self.contents = self.handler.get_content(
                requested_url, parameters, session)

        SessionStore.instance().upsert_session(self.session_id, session)

        if "userid" in parameters:  # if user wants to keep trace of read articles
            ArticleStore.instance().insert_article_as_read(
                parameters["userid"], requested_url)

        self._replace_prefix_urls()
        self._wrapped_html_content(parameters)

    def _process_rss(self, parameters: Dict[str, str]):
        self._log("/rss requested for module '%s' (%s)" %
                  (self.module_name, self.url))
        session: requests.Session = SessionStore.instance().get_session(self.session_id)
        self.content_type = FEED_XML_CONTENT_TYPE
        self.contents = self.handler.get_feed(parameters, session)
        self._arrange_feed(parameters)
        SessionStore.instance().upsert_session(self.session_id, session)

    def _arrange_feed(self, parameters: Dict[str, str]):
        """arrange feed by adding some pictures in description, ..."""

        if len(self.contents.strip()) > 0:
            # I probably do not use etree as I should
            self.contents = re.sub(
                r'<\?xml [^>]*?>', '', self.contents).strip()
            self.contents = re.sub(
                r'<\?xml-stylesheet [^>]*?>', '', self.contents).strip()
            try:
                dom = etree.fromstring(self.contents)

                # copy picture url from enclosure to a img tag in description (or add a generated one)
                for item in dom.xpath("//item"):
                    if self._arrange_feed_keep_item(item, parameters):
                        self._arrange_item(item, parameters)
                        self._arrange_feed_link(item, parameters)
                    else:
                        item.getparent().remove(item)

                self.contents = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                    etree.tostring(dom, encoding='unicode')
            except etree.XMLSyntaxError as e:
                self._log(
                    "Unable to parse rss feed for module '%s' (%s), let's proceed anyway: %s" % (self.module_name, self.url, str(e)))

    def _arrange_feed_keep_item(self, item: etree._Element, parameters: Dict[str, str]) -> bool:
        """return true if the item must not be deleted.
        The item must be deleted if the article has already been read.

        Arguments:
            item {etree._Element} -- rss feed item
            parameters {Dict[str, str]} -- url paramters which may contain the userid which is associated to read articles

        Returns:
            bool -- true if the item must not be deleted
        """
        feed_keep_item: bool = True
        if "userid" in parameters:
            for link in item.xpath(".//link"):  # NOSONAR
                parsed = urlparse.urlparse(link.text.strip())
                if "url" in parse_qs(parsed.query):
                    feed_keep_item = not ArticleStore.instance().has_article_been_read(
                        parameters["userid"], parse_qs(parsed.query)["url"][0])

        return feed_keep_item

    def _arrange_item(self, item: etree._Element, parameters: dict):
        descriptions = item.xpath(".//description")

        if len(descriptions) > 0:
            if descriptions[0].text is not None and len(descriptions[0].xpath('.//img')) == 0 and etree.tostring(descriptions[0], encoding='unicode').find("&lt;img ") == -1:
                # if description does not have a picture, add one from enclosure or media:content tag if any
                img_url: str = self._get_img_url(item)

                if img_url == "":
                    # uses the ThumbnailHandler to fetch an image from google search images
                    img_url = "%s/thumbnails?request=%s" % (
                        self.serving_url_prefix, quote_plus(re.sub(r"</?description>", "", etree.tostring(descriptions[0], encoding='unicode')).strip()))

                img = etree.Element("img")
                img.set("src", img_url)
                descriptions[0].append(img)

            n = self._get_source(item)
            if n is not None:
                descriptions[0].append(n)

            description_xml = etree.tostring(
                descriptions[0], encoding='unicode')
            description_xml = re.sub(
                r'<description[^>]*>', "", description_xml)
            description_xml = description_xml.replace("</description>", "")
            parent_obj = descriptions[0].getparent()
            parent_obj.remove(descriptions[0])

            description = etree.Element("description")
            description.text = html.unescape(description_xml.strip()).replace("&nbsp;", " ")
            parent_obj.append(description)

            if "debug" in parameters and parameters["debug"] == "true":
                p = etree.Element("p")
                i = etree.Element("i")
                i.text = "Session id: %s" % self.session_id
                p.append(i)
                descriptions[0].append(p)

    def _arrange_feed_link(self, item: etree._Element, parameters: Dict[str, str]):
        """arrange feed link, by adding dark and userid parameters if required

        Arguments:
            item {etree._Element} -- rss item
            parameters {Dict[str, str]} -- url parameters, one of them may be the dark boolean
        """
        suffix_url: str = ""
        for parameter in parameters:
            if parameter in ["dark", "debug", "userid", "plain"]:
                suffix_url += "&%s=%s" % (parameter, parameters[parameter])

        if suffix_url != "":
            for link in item.xpath(".//link"):
                link.text = "%s%s" % (link.text.strip(), suffix_url)

    def _get_source(self, node: etree) -> Optional[etree._Element]:
        """get source url from link in 'url' parameter

        Arguments:
            node {etree} -- rss item node

        Returns:
            etree -- a node having the source url
        """
        n: etree = None
        links = node.xpath(".//link")
        if len(links) > 0:
            parsed = urlparse.urlparse(links[0].text.strip())
            if "url" in parse_qs(parsed.query):
                a = etree.Element("a")
                a.set("href", parse_qs(parsed.query)["url"][0])
                a.text = "Source"
                n = etree.Element("p")
                n.append(a)
        return n

    def _get_img_url(self, node: etree) -> str:
        """get img url from enclosure or media:content tag if any

        Arguments:
            node {etree} -- item node of rss feed

        Returns:
            str -- the url of the image found in enclosure or media:content tag
        """
        img_url = ""
        enclosures = node.xpath(".//enclosure")
        # media:content tag
        medias = node.xpath(".//*[local-name()='content'][@url]")
        if len(enclosures) > 0:
            img_url = enclosures[0].get('url')
        elif len(medias) > 0:
            img_url = medias[0].get('url')
        return img_url

    def _extract_path_and_parameters(self, url: str) -> Tuple[str, dict]:
        """Extract url path and parameters (and decrypt them if they were crypted)

        Arguments:
            url {str} -- url (path + parameters, fragments are ignored)

        Returns:
            Tuple[str, dict] -- the path and the parameters in a dictionary
        """
        parsed = urlparse.urlparse(url)
        path: str = parsed.netloc + parsed.path
        parameters: dict = {}
        params: dict = parse_qs(parsed.query)
        for k in params:
            parameters[k] = self._get_parameter_value(params[k][0])

        return path, parameters

    def _get_parameter_value(self, v: str) -> str:
        """Get the parameter value. If the value were crypted, decrypt it.

        Arguments:
            v {str} -- given value from url

        Returns:
            str -- value url decoded and decrypted (if needed)
        """
        value = unquote_plus(v)
        if self.fernet is not None and value.find(ENCRYPTED_PREFIX) > -1:
            try:
                crypted_value = value[len(ENCRYPTED_PREFIX):]
                value = self.fernet.decrypt(
                    crypted_value.encode("ascii")).decode("ascii")
            except InvalidToken as e:
                self._log("Error decrypting : %s" % str(e))

        return value

    def _wrapped_html_content(self, parameters: dict):
        """wrap the html content with header, body and some predefined styles"""
        style: str = """
                #pyrssw_wrapper {
                    max-width:800px;
                    margin:auto;
                    line-height:1.6em;
                }
                h1 {
                    line-height:1em;
                }

                video {
                    max-width:500px!important;
                }

                img {
                    max-width:500px!important;
                }
        """
        source: str = ""
        domain: str = ""
        if "url" in parameters:
            source = "<em><a href='%s'>Source</em>" % parameters["url"]
            domain = urlparse.urlparse(parameters["url"]).netloc
        if "dark" in parameters and parameters["dark"] == "true":
            style += """
                body {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                a {
                    color:#0080ff
                }
            """

        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <link rel="icon" href="https://icons.duckduckgo.com/ip3/%s.ico"/>
                            <style>
                            %s
                            * {
                                font-family: "Marr Sans",Helvetica,Arial,Roboto,sans-serif
                            }
                            </style>
                        </head>
                        <body>
                            <div id=\"pyrssw_wrapper\">
                                %s
                                <br/>
                                <br/>
                                <hr/>
                                %s
                            </div>
                        </body>
                    </html>""" % (domain, style, self.contents, source)

    def _replace_prefix_urls(self):
        """Replace relative urls by absolute urls using handler prefix url"""

        def _replace_urls_process_links(dom: etree, attribute: str):
            for o in dom.xpath("//*[@%s]" % attribute):
                if o.attrib[attribute].startswith("//"):
                    protocol: str = "http:"
                    if self.handler.get_original_website().find("https") > -1:
                        protocol = "https:"
                    o.attrib[attribute] = protocol + o.attrib[attribute]
                elif o.attrib[attribute].startswith("/"):
                    o.attrib[attribute] = self.handler.get_original_website(
                    ) + o.attrib[attribute][1:]

        if self.handler.get_original_website() != '':
            dom = etree.HTML(self.contents)
            if dom is not None:
                _replace_urls_process_links(dom, "href")
                _replace_urls_process_links(dom, "src")
                self.contents = etree.tostring(dom, encoding='unicode').replace(
                    "<html>", "").replace("</html>", "").replace("<body>", "").replace("</body>", "")
