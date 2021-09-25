from handlers.content.content_processor import ContentProcessor
from typing import Dict, Optional, Tuple, Type, cast
import traceback
import requests
import urllib.parse as urlparse
from urllib.parse import parse_qs, unquote_plus
from cryptography.fernet import Fernet, InvalidToken
from handlers.feed_type.atom_arranger import AtomArranger
from handlers.feed_type.rss2_arranger import RSS2Arranger
from handlers.request_handler import RequestHandler
from pyrssw_handlers.abstract_pyrssw_request_handler import (
    ENCRYPTED_PREFIX, PyRSSWRequestHandler)

HTML_CONTENT_TYPE = "text/html; charset=utf-8"
FEED_XML_CONTENT_TYPE = "text/xml; charset=utf-8"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0"

# duration in minutes of a session
SESSION_DURATION = 30 * 60


class LauncherHandler(RequestHandler):
    """Handler which launches custom PyRSSWRequestHandler"""

    def __init__(self, module_name: str,
                 handlers: Dict[str, Type[PyRSSWRequestHandler]],
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
        if module_name in handlers:
            self.handler = handlers[module_name](
                self.fernet, self.handler_url_prefix)
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
        session: requests.Session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        if "url" in parameters:
            requested_url = parameters["url"]
        if not requested_url.startswith("https://") and not requested_url.startswith("http://"):
            requested_url += self.handler.get_original_website()

        if "plain" in parameters and parameters["plain"] == "true":
            # return the requested page without any modification
            self.contents = session.get(requested_url).text
        else:
            pyrssw_content = self.handler.get_content(
                requested_url, parameters, session)

            self.contents = ContentProcessor(
                handler=cast(PyRSSWRequestHandler, self.handler),
                url=url,
                contents=pyrssw_content.content,
                additional_css=pyrssw_content.css,
                parameters=parameters).process()

    def _process_rss(self, parameters: Dict[str, str]):
        self._log("/rss requested for module '%s' (%s)" %
                  (self.module_name, self.url))
        session: requests.Session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        self.content_type = FEED_XML_CONTENT_TYPE
        self.contents = self.handler.get_feed(parameters, session)
        if self.contents.find("<rss ") > -1:
            self.contents = RSS2Arranger(
                self.module_name, self.serving_url_prefix, self.session_id).arrange(parameters, self.contents, self.handler_url_prefix + "/rss", self.handler.get_favicon_url())
        elif self.contents.find("<feed ") > -1:
            self.contents = AtomArranger(
                self.module_name, self.serving_url_prefix, self.session_id).arrange(parameters, self.contents, self.handler_url_prefix + "/rss", self.handler.get_favicon_url())

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
            if params[k][0].find(ENCRYPTED_PREFIX) > -1:
                parameters["%s_crypted" % k] = params[k][0]

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
