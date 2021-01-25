from handlers.feed_type.atom_arranger import AtomArranger
from handlers.feed_type.rss2_arranger import RSS2Arranger
import traceback
import urllib.parse as urlparse
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote_plus
import requests
from cryptography.fernet import Fernet, InvalidToken
from lxml import etree
from typing_extensions import Type
from handlers.request_handler import RequestHandler
from pyrssw_handlers.abstract_pyrssw_request_handler import (
    ENCRYPTED_PREFIX, PyRSSWRequestHandler)
from storage.article_store import ArticleStore
from storage.session_store import SessionStore
from utils.dom_utils import to_string, xpath
import re

HTML_CONTENT_TYPE = "text/html; charset=utf-8"
FEED_XML_CONTENT_TYPE = "text/xml; charset=utf-8"

# duration in minutes of a session
SESSION_DURATION = 30 * 60
TWEETS_REGEX = re.compile(r'(?:https://twitter.com/)(?:.*)/status/(.*)')

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

        """
        self.twitter_api = None
        twitter_tokens = Config.instance().get_twitter_tokens()
        if twitter_tokens[TWITTER_CONSUMER_KEY] is not None:
            self.twitter_api = TwitterAPI(twitter_tokens[TWITTER_CONSUMER_KEY], twitter_tokens[TWITTER_CONSUMER_SECRET],
                                          twitter_tokens[TWITTER_ACCESS_TOKEN_KEY], twitter_tokens[TWITTER_ACCESS_TOKEN_SECRET], api_version='2')

        """
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

            """doc = Document(self.contents) #get a "readable" content
            readable_content: str = doc.summary()
            
            if readable_content != "<html><body/></html>":
                self.contents = readable_content
            else:
                self._log("The '%s' handler did not produce readable content for url '%s', let it potentially 'not readable'" % (self.handler.get_handler_name(), url))
            """
        SessionStore.instance().upsert_session(self.session_id, session)

        if "userid" in parameters:  # if user wants to keep trace of read articles
            ArticleStore.instance().insert_article_as_read(
                parameters["userid"], requested_url)

        self._post_processing(parameters)
        self._wrapped_html_content(parameters)

    def _process_rss(self, parameters: Dict[str, str]):
        self._log("/rss requested for module '%s' (%s)" %
                  (self.module_name, self.url))
        session: requests.Session = SessionStore.instance().get_session(self.session_id)
        self.content_type = FEED_XML_CONTENT_TYPE
        self.contents = self.handler.get_feed(parameters, session)
        if self.contents.find("<rss ") > -1:
            self.contents = RSS2Arranger(
                self.module_name, self.serving_url_prefix, self.session_id).arrange(parameters, self.contents)
        elif self.contents.find("<feed ") > -1:
            self.contents = AtomArranger(
                self.module_name, self.serving_url_prefix, self.session_id).arrange(parameters, self.contents)

        SessionStore.instance().upsert_session(self.session_id, session)

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
                @import url(https://fonts.googleapis.com/css?family=Roboto:100,100italic,300,300italic,400,400italic,500,500italic,700,700italic,900,900italic&subset=latin,latin-ext,cyrillic,cyrillic-ext,greek-ext,greek,vietnamese);

                body {
                    color: #TEXT_COLOR#;
                    background-color:#BACKGROUND_COLOR#;
                    font-family: Roboto;
                    font-weight: 300;
                    line-height: 150%;
                }
                #pyrssw_wrapper {
                    max-width:800px;
                    margin:auto;
                }
                #pyrssw_wrapper * {max-width: 100%; word-break: break-word}
                #pyrssw_wrapper h1, #pyrssw_wrapper h2 {font-weight: 300; line-height: 130%}
                #pyrssw_wrapper h1 {font-size: 170%; margin-bottom: 0.1em}
                #pyrssw_wrapper h2 {font-size: 140%}
                #pyrssw_wrapper a {color: #0099CC}
                #pyrssw_wrapper h1 a {color: inherit; text-decoration: none}
                #pyrssw_wrapper img {height: auto; float:left; margin-right:15px}
                #pyrssw_wrapper div img {float:left;}
                #pyrssw_wrapper pre {white-space: pre-wrap; direction: ltr;}
                #pyrssw_wrapper blockquote {border-left: thick solid #QUOTE_LEFT_COLOR#; background-color:#BG_BLOCKQUOTE#; margin: 0.5em 0 0.5em 0em; padding: 0.5em}
                #pyrssw_wrapper p {margin: 0.8em 0 0.8em 0}
                #pyrssw_wrapper p.subtitle {color: #SUBTITLE_COLOR#; border-top:1px #SUBTITLE_BORDER_COLOR#; border-bottom:1px #SUBTITLE_BORDER_COLOR#; padding-top:2px; padding-bottom:2px; font-weight:600 }
                #pyrssw_wrapper ul, #pyrssw_wrapper ol {margin: 0 0 0.8em 0.6em; padding: 0 0 0 1em}
                #pyrssw_wrapper ul li, #pyrssw_wrapper ol li {margin: 0 0 0.8em 0; padding: 0}
                #pyrssw_wrapper hr {border : 1px solid #HR_COLOR#;  background-color: #HR_COLOR#}
                #pyrssw_wrapper strong {font-weight:400}
                #pyrssw_wrapper figure {margin:0}
                #pyrssw_wrapper figure img {width:100%;float:none}
                #pyrssw_wrapper iframe {width:100%;min-height:500px;height:auto}
                #pyrssw_wrapper blockquote.twitter-tweet {background: transparent;border-left-color: transparent;}
                #pyrssw_wrapper blockquote.twitter-tweet iframe {min-height:auto}
                #pyrssw_wrapper .twitter-tweet {margin: 0 auto}

                .pyrssw_youtube, #pyrssw_wrapper video {
                    max-width:100%!important;
                    width: auto;
                    height: auto;
                    margin: 0 auto;
                    display:block;
                }

                .pyrssw_centered {
                    text-align:center;
                }

                .pyrssw-source {
                    text-align: right;
                    font-style: italic;
                }

                #pyrssw_wrapper img {
                    max-width:100%!important;
                    width: auto;
                    height: auto;
                }
                
        """
        source: str = ""
        domain: str = ""
        if "url" in parameters:
            source = "<p class='pyrssw-source'><a href='%s'>Source</a></p>" % parameters["url"]
            domain = urlparse.urlparse(parameters["url"]).netloc

        text_color = "#000000"
        bg_color = "#f6f6f6"
        quote_left_color = "#a6a6a6"
        quote_bg_color = "#e6e6e6"
        subtitle_color = "#666666"
        subtitle_border_color = "#ddd"
        hr_color = "#a6a6a6"
        if "dark" in parameters and parameters["dark"] == "true":
            text_color = "#8c8c8c"
            bg_color = "#222222"
            quote_left_color = "#686b6f"
            quote_bg_color = "#383b3f"
            subtitle_color = "#8c8c8c"
            subtitle_border_color = "#303030"
            hr_color = "#686b6f"
            style += """
                body {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                a {
                    color:#0080ff
                }
            """

        style = style.replace("#QUOTE_LEFT_COLOR#", quote_left_color)\
                     .replace("#BG_BLOCKQUOTE#", quote_bg_color)\
                     .replace("#SUBTITLE_COLOR#", subtitle_color)\
                     .replace("#SUBTITLE_BORDER_COLOR#", subtitle_border_color)\
                     .replace("#TEXT_COLOR#", text_color)\
                     .replace("#BACKGROUND_COLOR#", bg_color)\
                     .replace("#HR_COLOR#", hr_color)

        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <link rel="icon" href="https://icons.duckduckgo.com/ip3/%s.ico"/>
                            <style>
                            %s
                            </style>
                        </head>
                        <body>
                            <div id=\"pyrssw_wrapper\">
                                %s
                                <br/>
                                <hr/>
                                %s
                            </div>
                        </body>
                    </html>""" % (domain, style, self.contents, source)

    def _manage_title(self, dom: etree._Element, parameters: dict):
        if "hidetitle" in parameters and parameters["hidetitle"] == "true":
            h1s = xpath(dom, "//h1")
            if len(h1s) > 0:
                h1s[0].getparent().remove(h1s[0])

    def _replace_prefix_urls(self, parameters: dict, dom: etree._Element):
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
            if dom is not None:
                _replace_urls_process_links(dom, "href")
                _replace_urls_process_links(dom, "src")
                self._manage_title(dom, parameters)
                self.contents = to_string(dom).replace(
                    "<html>", "").replace("</html>", "").replace("<body>", "").replace("</body>", "")

    def _post_processing(self, parameters: dict):
        dom = etree.HTML(self.contents)
        self._post_process_tweets(parameters, dom)
        self._replace_prefix_urls(parameters, dom)
        self.contents = self.contents.replace("data-src-lazyload", "src")
        self.contents = self.contents.replace("</br>", "")
    
    def _post_process_tweets(self, parameters:dict, dom: etree._Element):
        """
            Process tweets, to replace twitter url by tweets' content
        """

        has_tweets: bool = False
        for a in xpath(dom, "//a[contains(@href,'https://twitter.com/')]"):
            m = re.match(TWEETS_REGEX, a.attrib["href"])
            if m is not None:
                tweet_id: str = m.group(1)
                has_tweets = True
                script = etree.Element("script")
                script.text = """
                    window.onload = (function(){
                        var tweet_%s = document.getElementById("tweet_%s");
                        twttr.widgets.createTweet(
                        '%s', tweet_%s,
                        {
                            conversation : 'none',    // or all
                            cards        : 'visible',
                            theme        : '%s'
                        });
                    });
                """ % (
                    tweet_id,
                    tweet_id,
                    tweet_id,
                    tweet_id,
                    "dark" if "dark" in parameters and parameters["dark"] == "true" else "light"
                
                )
                tweet_div = etree.Element("div")
                tweet_div.set("id", "tweet_%s" % tweet_id)
                a.getparent().append(script)
                a.getparent().append(tweet_div)
                a.getparent().remove(a)

        
        if has_tweets:
            script = etree.Element("script")
            script.set("src", "https://platform.twitter.com/widgets.js")
            script.set("sync", "")
            dom.append(script)

