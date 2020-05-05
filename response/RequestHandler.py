import logging
import datetime
import lxml
import traceback
import urllib.parse
import re
from typing import Tuple



class RequestHandler():
    """Main instance for every handler.

    get_feed, get_content and get_content_type must be overridden by every new Handlers.

    - getFeed :
        Takes a dictionary of parameters and must return the xml of the rss feed

    - getContent :
        Takes an url and a dictionary of parameters and must return the result content.
        If the content returned is not HTML, the function getContentType must also be overridden (see ThumbnailsHandler.py)
    """

    def __init__(self, url_prefix, handler_name, original_website, rss_url=""):
        self.content_type = ""
        self.handler_name = handler_name
        self.rss_url = rss_url
        self.original_website = original_website
        self.url_prefix = "%s/%s/" % (url_prefix, handler_name)
        self.url_root = url_prefix
        self.logger = logging.getLogger()
        self.contents: str = ""
        self.HTML_CONTENT_TYPE = "text/html; charset=utf-8"

    def get_user_agent(self):
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    def _log(self, msg):
        self.logger.info(
            "[" + datetime.datetime.now().strftime("%Y-%m-%d - %H:%M") + "] - - " + msg)

    def get_contents(self) -> str:
        return self.contents

    def read(self) -> str:
        return self.contents

    def set_status(self, status: int):
        self.status = status

    def get_status(self) -> int:
        return self.status

    def get_content_type(self) -> str:
        return self.content_type

    def get_type(self) -> str:
        return 'static'

    # must be overwritten by handlers
    def get_feed(self, parameters: dict) -> str:
        return ''

    # must be overwritten by handlers
    def get_content(self, url: str, parameters: dict) -> str:
        return ''

    def process(self, url: str) -> bool:
        """process the url, finds the handler to use depending on the url"""
        try:
            url, parameters = self._get_module_name_from_url(url)
            if url.find("/rss") == 0:
                self._log("%s /rss requested" % self.handler_name)
                self.contents = self._arrange_feed(self.get_feed(parameters))
                # add dark request for all rss links
                self.contents = self.contents.replace("%s?" % self.url_prefix, "%s?%s" % (
                    self.url_prefix, self._get_dark_parameters(parameters)))
                self.content_type = "text/xml; charset=utf-8"
            else:
                self._log("%s content page requested: %s" %
                          (self.handler_name, url))
                request_url = url
                # default contentType, can be overridden by handlers
                self.content_type = self.HTML_CONTENT_TYPE
                if "url" in parameters:
                    request_url = parameters["url"]
                if not request_url.startswith("https://") and not request_url.startswith("http://"):
                    self.contents = self.get_content(
                        self.original_website + request_url, parameters)
                else:
                    self.contents = self.get_content(request_url, parameters)

                if self.content_type == self.HTML_CONTENT_TYPE: #if not overridden by handlers
                    self._wrapped_html_content(parameters)

            self.set_status(200)
            return True

        except Exception as e:
            self.contents = "<html><body>" + url + "<br/>" + \
                str(e) + "<br/><pre>" + traceback.format_exc() + \
                "</pre></body></html>"
            self.content_type = "text/html; utf-8"
            self.set_status(500)
            return False

    def _arrange_feed(self, content: str) -> str:
        """arrange feed by adding some pictures in description, ..."""

        feed = content
        if len(content.strip()) > 0:
            # I probably do not use etree as I should
            feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
            feed = re.sub(r'<\?xml-stylesheet [^>]*?>', '', feed).strip()
            dom = lxml.etree.fromstring(feed)
            
            # copy picture url from enclosure to a img tag in description (or add a generated one)
            for item in dom.xpath("//item"):
                descriptions = item.xpath(".//description")
                if len(descriptions) > 0 and descriptions[0].text.find('<img ') == -1:
                    # if description does not have a picture, add one from enclosure or media:content tag if any
                    enclosures = item.xpath(".//enclosure")
                    # media:content tag
                    medias = item.xpath(".//*[local-name()='content'][@url]")
                    img_url = ""
                    if len(enclosures) > 0:
                        img_url = enclosures[0].get('url')
                    elif len(medias) > 0:
                        img_url = medias[0].get('url')

                    if img_url != "":
                        descriptions[0].text = '<img src="%s"/>%s' % (
                            img_url, descriptions[0].text)
                    else:  # uses the ThumbnailHandler to fetch an image from google search images
                        descriptions[0].text = '<img src="%s/thumbnails?request=%s"/>%s' % (
                            self.url_root, urllib.parse.quote_plus(descriptions[0].text), descriptions[0].text)

            feed = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                lxml.etree.tostring(dom, encoding='unicode')

        return feed

    def _get_module_name_from_url(self, url: str) -> Tuple[str, dict]:
        """get the module name and the url requested from the url"""
        parameters: dict = {}
        new_url: str = url
        parts = url.split('?')
        if len(parts) > 1:
            new_url = parts[0]
            params = parts[1].split('&')
            for param in params:
                keyv = param.split('=')
                if len(keyv) == 2:
                    parameters[urllib.parse.unquote_plus(
                        keyv[0])] = urllib.parse.unquote_plus(keyv[1])

        return new_url, parameters

    def _wrapped_html_content(self, parameters: dict):
        """wrap the html content with header, body and some predefined styles"""
        dark_style: str = ""
        source: str = ""
        if "url" in parameters:
            source = "<em><a href='%s'>Source</em>" % parameters["url"]
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = """@media (prefers-color-scheme: dark) {
                                body {
                                    background-color: #111;
                                    color: #ccc;
                                }
                                a {
                                    color:#0080ff
                                }
                                * {
                                    font-family: "Marr Sans",Helvetica,Arial,Roboto,sans-serif
                                }
                            }
                        """

        # TODO remove head and body if previously exists and logs it
        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <style>%s</style>
                        </head>
                        <body>
                            %s
                            <br/>
                            <br/>
                            <hr/>
                            %s
                        </body>
                    </html>""" % (dark_style, self.contents, source)

    def _get_dark_parameters(self, parameters: dict) -> str:
        """get the url parameter if dark=true is defined in parameters"""
        dark_style: str = ""
        if "dark" in parameters and parameters["dark"] == "true":
            dark_style = "dark=true&amp;"
        return dark_style
