import base64
import re
import traceback
import urllib.parse
from typing import List, Optional, Tuple

from cryptography.fernet import Fernet
from lxml import etree
from typing_extensions import Type

from handlers.request_handler import RequestHandler
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

HTML_CONTENT_TYPE = "text/html; charset=utf-8"
FEED_XML_CONTENT_TYPE = "text/xml; charset=utf-8"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0"


class LauncherHandler(RequestHandler):
    """Handler which launches custom PyRSSWRequestHandler"""

    def __init__(self, module_name: str, handlers: List[Type[PyRSSWRequestHandler]], serving_url_prefix: Optional[str], url: str, crypto_key: bytes):
        super().__init__()
        self.handler: Optional[PyRSSWRequestHandler] = None
        self.serving_url_prefix: Optional[str] = serving_url_prefix
        self.handler_url_prefix: str = "%s/%s" % (
            serving_url_prefix, module_name)
        self.url: str = url
        self.crypto: Fernet = Fernet(crypto_key)
        for h in handlers:  # find handler from module_name
            if h.get_handler_name() == module_name:
                self.handler = h(self.handler_url_prefix)
                break

        if not self.handler is None:
            self.process()
        else:
            raise Exception("No handler found for name '%s'" % module_name)

    def process(self):
        """process the url, finds the handler to use depending on the url"""
        try:
            url, parameters = self._get_module_name_from_url(self.url)
            if url.find("/rss") == 0:
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
        self._log("content page requested: %s" % url)
        request_url = url
        self.content_type = HTML_CONTENT_TYPE
        if "url" in parameters:
            request_url = parameters["url"]
        if not request_url.startswith("https://") and not request_url.startswith("http://"):
            self.contents = self.handler.get_content(
                self.handler.get_original_website() + request_url, parameters)
        else:
            self.contents = self.handler.get_content(request_url, parameters)

        self._replace_prefix_urls()
        self._wrapped_html_content(parameters)

    def _process_rss(self, parameters):
        self._log("/rss requested")
        self.content_type = FEED_XML_CONTENT_TYPE
        self.contents = self.handler.get_feed(parameters)
        self._arrange_feed()
        # add dark request for all rss links if required
        self.contents = self.contents.replace("%s?" % self.handler_url_prefix, "%s?%s" % (
            self.handler_url_prefix, self._get_dark_parameters(parameters)))

    def _arrange_feed(self):
        """arrange feed by adding some pictures in description, ..."""

        if len(self.contents.strip()) > 0:
            # I probably do not use etree as I should
            self.contents = re.sub(
                r'<\?xml [^>]*?>', '', self.contents).strip()
            self.contents = re.sub(
                r'<\?xml-stylesheet [^>]*?>', '', self.contents).strip()
            dom = etree.fromstring(self.contents)

            # copy picture url from enclosure to a img tag in description (or add a generated one)
            for item in dom.xpath("//item"):
                descriptions = item.xpath(".//description")
                if len(descriptions) > 0 and descriptions[0].text.find('<img ') == -1:
                    # if description does not have a picture, add one from enclosure or media:content tag if any
                    img_url = self._get_img_url(item)

                    if img_url != "":
                        descriptions[0].text = '<img src="%s"/>%s' % (
                            img_url, descriptions[0].text)
                    else:  # uses the ThumbnailHandler to fetch an image from google search images
                        descriptions[0].text = '<img src="%s/thumbnails/%s"/>%s' % (
                            self.serving_url_prefix, urllib.parse.quote_plus(descriptions[0].text), descriptions[0].text)

            self.contents = '<?xml version="1.0" encoding="UTF-8"?>\n' + \
                etree.tostring(dom, encoding='unicode')

    def _get_img_url(self, node: etree):
        """ get img url from enclosure or media:content tag if any """
        img_url = ""
        enclosures = node.xpath(".//enclosure")
        # media:content tag
        medias = node.xpath(".//*[local-name()='content'][@url]")
        if len(enclosures) > 0:
            img_url = enclosures[0].get('url')
        elif len(medias) > 0:
            img_url = medias[0].get('url')
        return img_url

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
                        keyv[0])] = self._get_parameter_value(keyv[1])

        return new_url, parameters

    def _get_parameter_value(self, v: str) -> str:
        """Get the parameter value. If the value were crypted, decrypt it.

        Arguments:
            v {str} -- given value from url

        Returns:
            str -- value url decoded and decrypted (if needed)
        """
        value = urllib.parse.unquote_plus(v)
        try:
            value = self.crypto.decrypt(value.encode('ascii'))
        except Exception:
            pass

        return value

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
                            }
                        """

        # TODO remove head and body if previously exists and logs it
        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <style>
                            %s
                            * {
                                font-family: "Marr Sans",Helvetica,Arial,Roboto,sans-serif
                            }
                            </style>
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

    def _replace_prefix_urls(self):
        if self.handler.get_original_website() != '':
            self.contents = self.contents.replace("a href='" + self.handler.get_original_website(),
                                                  "a href='" + self.handler_url_prefix)
            self.contents = self.contents.replace(
                'a href="' + self.handler.get_original_website(), 'a href="' + self.handler_url_prefix)
            self.contents = self.contents.replace(
                'href="/', 'href="' + self.handler.get_original_website())
            self.contents = self.contents.replace(
                "href='/", "href='" + self.handler.get_original_website())
            self.contents = self.contents.replace(
                'src="/', 'src="' + self.handler.get_original_website())
            self.contents = self.contents.replace(
                "src='/", "src='" + self.handler.get_original_website())
