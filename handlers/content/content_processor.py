import re
from lxml import etree
import urllib.parse as urlparse
from urllib.parse import unquote
from handlers.constants import GENERIC_PARAMETERS
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import to_string, translate_dom, xpath

TWEETS_REGEX = re.compile(
    r'(?:(?:https:)?//twitter.com/)(?:.*)/status/([^\?]*)')
PERCENTAGE_REGEX = re.compile(r'\d+(?:\.\d+)?%')


class ContentProcessor():
    """Generic processing of article content provided by handlers:
     - add CSS: font, pictures & video dimensions, ...
     - replace tweet links by tweet cards
     - apply parameters:
        - dark/white theme
        - font size
        - show/hide main article title
        - content translation
        - add a header with the handler name + link of the source article
    """

    def __init__(self, handler: PyRSSWRequestHandler, url: str, contents: str, additional_css: str, parameters: dict, handler_url_prefix: str) -> None:
        self.handler: PyRSSWRequestHandler = handler
        self.url: str = url
        self.contents: str = contents
        self.additional_css: str = additional_css
        self.parameters: dict = parameters
        self.handler_url_prefix: str = handler_url_prefix

    def process(self) -> str:
        self._post_processing()
        self._wrapped_html_content()
        return self.contents

    def _post_processing(self):
        if len(self.contents.strip()) > 0:
            #dom = etree.HTML(self.contents.replace("\n", ""), parser=None)
            dom = etree.HTML(self.contents, parser=None)
            self._process_lazyload_imgs(dom)
            self._post_process_tweets(dom)
            self._replace_prefix_urls(dom)
            self._manage_translation(dom)
            self._remove_imgs_without_src(dom)
            self._remove_duplicate_imgs(dom)
            self.contents = to_string(dom)\
                .replace("<html>", "")\
                .replace("</html>", "")\
                .replace("<body>", "")\
                .replace("</body>", "")\
                .replace("<video", "<video preload=\"none\"")

            self.contents = self.contents.replace("</br>", "")

    def _process_lazyload_imgs(self, dom: etree._Element):
        for img in xpath(dom, "//img"):
            for attr in img.attrib:
                if attr.endswith("-src") or attr.find("-src-") > -1:
                    img.attrib["src"] = img.attrib[attr]
                    break

    def _remove_imgs_without_src(self, dom: etree._Element):
        for img in xpath(dom, "//img"):
            if img.attrib.get("src", "").strip() == "":
                img.getparent().remove(img)
    
    def _remove_duplicate_imgs(self, dom: etree._Element):
        imgs = []
        for img in xpath(dom, "//img"):
            if img.attrib.get("src") in imgs:
                img.getparent().remove(img)
            else:
                imgs.append(img.attrib.get("src"))

    def _post_process_tweets(self, dom: etree._Element):
        """
            Process tweets, to replace twitter url by tweets' content
        """

        has_tweets: bool = False
        for a in xpath(dom, "//a[contains(@href,'https://twitter.com/')]|//a[contains(@href,'//twitter.com/')]"):
            m = re.match(TWEETS_REGEX, a.attrib["href"])
            if m is not None:
                tweet_id: str = m.group(1)
                has_tweets = True
                script = etree.Element("script")
                script.text = """
                    window.addEventListener("DOMContentLoaded", function() {
                        var tweet_%s = document.getElementById("tweet_%s");
                        twttr.widgets.createTweet(
                        '%s', tweet_%s,
                        {
                            conversation : 'none',    // or all
                            cards        : 'visible',
                            theme        : '%s'
                        });
                    });
                    document.getElementById("parent-%s").style.display = "none";
                """ % (
                    tweet_id,
                    tweet_id,
                    tweet_id,
                    tweet_id,
                    "dark" if "dark" in self.parameters and self.parameters[
                        "dark"] == "true" else "light",
                    tweet_id
                )
                tweet_div = etree.Element("div")
                tweet_div.set("id", "tweet_%s" % tweet_id)
                a.getparent().addnext(script)
                a.getparent().addnext(tweet_div)
                a.getparent().set("id", "parent-%s" % tweet_id)
                a.getparent().remove(a)

        if has_tweets:
            script = etree.Element("script")
            script.set("src", "https://platform.twitter.com/widgets.js")
            script.set("sync", "")
            dom.append(script)

    def _manage_translation(self, dom: etree._Element):
        if "translateto" in self.parameters:
            translate_dom(dom, self.parameters["translateto"], self.url)

    def _get_header(self) -> str:
        header: str = """
        <script>
            var observer = new IntersectionObserver(
                (entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.intersectionRatio > 0.0) {
                            img = entry.target;
                            if (!img.hasAttribute('src')) {
                                img.setAttribute('src', img.dataset.src);
                            }
                        }
                    });
                },
                {
                    rootMargin:"200px"
                }
            )
            window.addEventListener("DOMContentLoaded", function() {
                for (let img of document.querySelectorAll("img[data-src]")) {
                    observer.observe(img);
                }
            });
        </script>
"""
        if "header" in self.parameters and self.parameters["header"].lower() == "true":
            header += """<script>
	/*
		By Osvaldas Valutis, www.osvaldas.info
		Available for use under the MIT License
	*/

	window.addEventListener("DOMContentLoaded", function() {
        ;( function ( document, window, index )
        {
            'use strict';

            var elSelector	= '.pyrssw_content_header',
                element		= document.querySelector( elSelector );

            if( !element ) return true;

            var elHeight		= 0,
                elTop			= 0,
                dHeight			= 0,
                wHeight			= 0,
                wScrollCurrent	= 0,
                wScrollBefore	= 0,
                wScrollDiff		= 0;

            window.addEventListener( 'scroll', function()
            {
                elHeight		= element.offsetHeight;
                dHeight			= document.body.offsetHeight;
                wHeight			= window.innerHeight;
                wScrollCurrent	= window.pageYOffset;
                wScrollDiff		= wScrollBefore - wScrollCurrent;
                elTop			= parseInt( window.getComputedStyle( element ).getPropertyValue( 'top' ) ) + wScrollDiff;

                if( wScrollCurrent <= 0 ) // scrolled to the very top; element sticks to the top
                    element.style.top = '0px';

                else if( wScrollDiff > 0 ) // scrolled up; element slides in
                    element.style.top = ( elTop > 0 ? 0 : elTop ) + 'px';

                else if( wScrollDiff < 0 ) // scrolled down
                {
                    //if( wScrollCurrent + wHeight >= dHeight - elHeight )  // scrolled to the very bottom; element slides in
                    //    element.style.top = ( ( elTop = wScrollCurrent + wHeight - dHeight ) < 0 ? elTop : 0 ) + 'px';

                    //else // scrolled down; element slides out
                        element.style.top = ( Math.abs( elTop ) > elHeight ? -elHeight : elTop ) + 'px';
                }

                wScrollBefore = wScrollCurrent;
            });

        }( document, window, 0 ));
    });
</script>
            <header class="pyrssw_content_header"><div class="container"><a href="%s" target="_blank"><img src="%s"/>%s</a></div></header>""" % (
                self.parameters["url"], self.handler.get_favicon_url(self.parameters), self.handler.get_handler_name(self.parameters))

        return header

    def _wrapped_html_content(self):
        """wrap the html content with header, body and some predefined styles"""

        style: str = """
                @import url(https://fonts.googleapis.com/css?family=Roboto:100,100italic,300,300italic,400,400italic,500,500italic,700,700italic,900,900italic&subset=latin,latin-ext,cyrillic,cyrillic-ext,greek-ext,greek,vietnamese);

                body {
                    color: #TEXT_COLOR#;
                    background-color:#BACKGROUND_COLOR#;
                    font-family: Roboto;
                    font-weight: 300;
                    line-height: 150%;
                    font-size: #GLOBAL_FONT_SIZE#;
                    margin:0;
                    #BODY_PADDING_FOR_HEADER#
                }

                @media screen and (max-width : 640px) {
                    body {
                        font-size:#SMARTPHONE_GLOBAL_FONT_SIZE#;
                    }
                }

                #pyrssw_wrapper {
                    max-width:800px;
                    margin:auto;
                    padding:8px;
                }
                #pyrssw_wrapper * {max-width: 100%; word-break: break-word}
                #pyrssw_wrapper h1, #pyrssw_wrapper h2 {font-weight: 300; line-height: 130%}
                #pyrssw_wrapper h1 {font-size: 170%; margin-bottom: 0.1em}
                #pyrssw_wrapper h2 {font-size: 140%}
                #pyrssw_wrapper h1 span, #pyrssw_wrapper h2 span {padding-right:10px;}
                #pyrssw_wrapper a {color: #0099CC}
                #pyrssw_wrapper h1 a {color: inherit; text-decoration: none}
                #pyrssw_wrapper img {height: auto; margin-right:15px;vertical-align:middle;}
                #pyrssw_wrapper pre {white-space: pre-wrap; direction: ltr;}
                #pyrssw_wrapper blockquote {border-left: thick solid #QUOTE_LEFT_COLOR#; background-color:#BG_BLOCKQUOTE#; margin: 0.5em 0 0.5em 0em; padding: 0.5em}
                #pyrssw_wrapper p {margin: 0.8em 0 0.8em 0}
                #pyrssw_wrapper p.subtitle {color: #SUBTITLE_COLOR#; border-top:1px #SUBTITLE_BORDER_COLOR#; border-bottom:1px #SUBTITLE_BORDER_COLOR#; padding-top:2px; padding-bottom:2px; font-weight:600 }
                #pyrssw_wrapper ul, #pyrssw_wrapper ol {margin: 0 0 0.8em 0.6em; padding: 0 0 0 1em}
                #pyrssw_wrapper ul li, #pyrssw_wrapper ol li {margin: 0 0 0.8em 0; padding: 0}
                #pyrssw_wrapper hr {border : 1px solid #HR_COLOR#;  background-color: #HR_COLOR#}
                #pyrssw_wrapper strong {font-weight:400}
                #pyrssw_wrapper figure {margin:0}
                #pyrssw_wrapper figure img {width:100%!important;float:none}
                #pyrssw_wrapper iframe {width:100%;position:unset!important;min-height: max(220px,20vw);}
                #pyrssw_wrapper iframe.instagram-media {margin:auto!important;}
                #pyrssw_wrapper table, th, td {border: 1px solid;border-collapse: collapse;padding: 5px;}
                #pyrssw_wrapper blockquote.twitter-tweet {background: transparent;border-left-color: transparent;}
                #pyrssw_wrapper .twitter-tweet iframe {min-height:auto}
                #pyrssw_wrapper .twitter-tweet {margin: 0 auto}
                .pyrssw_content_header .container {height: 100%;overflow: hidden;}
                .pyrssw_content_header {position: fixed;z-index: 1;top: 0;left: 0;width:100%;height:32px;padding: 5px;background-color:#HEADER_CSS_BG_COLOR#;text-align: center;border-bottom: 2px solid #HEADER_CSS_BORDER_COLOR#}
                .pyrssw_content_header a {color:#HEADER_CSS_A_COLOR#;text-decoration:none;font-weight:500;font-size:20px;}
                .pyrssw_content_header img {margin-right:10px;vertical-align:middle;height:32px}

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
        if "url" in self.parameters:
            source = "<p class='pyrssw-source'><a href='%s'>Source</a></p>" % self.parameters["url"]
            domain = urlparse.urlparse(self.parameters["url"]).netloc

        text_color = "#000000"
        bg_color = "#f6f6f6"
        quote_left_color = "#a6a6a6"
        quote_bg_color = "#e6e6e6"
        subtitle_color = "#666666"
        subtitle_border_color = "#ddd"
        hr_color = "#a6a6a6"
        header_css_bg_color = "#ccc"
        header_css_border_color = "#888"
        header_css_a_color = "#000"
        body_padding_for_header = ""

        if "dark" in self.parameters and self.parameters["dark"] == "true":
            text_color = "#8c8c8c"
            bg_color = "#222222"
            quote_left_color = "#686b6f"
            quote_bg_color = "#383b3f"
            subtitle_color = "#8c8c8c"
            subtitle_border_color = "#303030"
            hr_color = "#686b6f"
            header_css_bg_color = "#353535"
            header_css_border_color = "#555"
            header_css_a_color = "#adadad"
            style += """
                body {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                }
                a {
                    color:#0080ff
                }
            """

        if "header" in self.parameters and self.parameters["header"] == "true":
            body_padding_for_header = "padding-top:40px;"

        global_font_size = "100%"
        smartphone_global_font_size = "120%"
        if "fontsize" in self.parameters and re.match(PERCENTAGE_REGEX, self.parameters["fontsize"]):
            global_font_size = self.parameters["fontsize"]
            smartphone_global_font_size = str(
                int(int(global_font_size.split("%")[0])) * 1.2) + "%"

        style = style.replace("#QUOTE_LEFT_COLOR#", quote_left_color)\
                     .replace("#BG_BLOCKQUOTE#", quote_bg_color)\
                     .replace("#SUBTITLE_COLOR#", subtitle_color)\
                     .replace("#SUBTITLE_BORDER_COLOR#", subtitle_border_color)\
                     .replace("#TEXT_COLOR#", text_color)\
                     .replace("#BACKGROUND_COLOR#", bg_color)\
                     .replace("#HR_COLOR#", hr_color)\
                     .replace("#GLOBAL_FONT_SIZE#", global_font_size)\
                     .replace("#SMARTPHONE_GLOBAL_FONT_SIZE#", smartphone_global_font_size)\
                     .replace("#HEADER_CSS_BG_COLOR#", header_css_bg_color)\
                     .replace("#HEADER_CSS_BORDER_COLOR#", header_css_border_color)\
                     .replace("#HEADER_CSS_A_COLOR#", header_css_a_color)\
                     .replace("#BODY_PADDING_FOR_HEADER#", body_padding_for_header)

        self.contents = """<!DOCTYPE html>
                    <html>
                        <head>
                            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                            <meta name='viewport' content='width=device-width'/>
                            <link rel="icon" href="https://icons.duckduckgo.com/ip3/%s.ico"/>
                            <style>
                            %s

                            %s
                            </style>
                        </head>
                        <body>
                            %s
                            <div id="pyrssw_wrapper">
                                <div id="%s_handler">
                                    %s
                                </div>
                                <br/>
                                <hr/>
                                %s
                            </div>
                        </body>
                    </html>""" % (domain, style, self.additional_css, self._get_header(),  self.handler.get_handler_name_for_url(), self.contents, source)

    def _replace_prefix_urls(self, dom: etree._Element):
        """Replace relative urls by absolute urls using handler prefix url"""

        if self.handler.get_original_website() != '' and dom is not None:
            self._replace_urls_process_links(dom, "href")
            self._replace_urls_process_links(dom, "src")
            self._manage_title(dom)

        if self.parameters.get("internallinksinpyrssw", "true") == "true":
            # replace internal links using pyrssw prefix to display linked articles using filtering process
            suffix_url: str = ""
            for parameter in self.parameters:
                if not parameter.endswith("_crypted") and parameter != "url":
                    if "%s_crypted" % parameter not in self.parameters:
                        suffix_url += "&%s=%s" % (parameter,
                                                  self.parameters[parameter])
                    else:
                        suffix_url += "&%s=%s" % (parameter,
                                                  self.parameters["%s_crypted" % parameter])

            urlp = urlparse.urlparse(self.parameters.get(
                "rssurl", self.parameters.get("url", "")))
            for o in dom.xpath("//a[@href]"):
                if o.attrib.get("href", "").startswith("%s://%s" % (urlp.scheme, urlp.hostname)):
                    o.attrib["href"] = "%s?url=%s%s" % (
                        self.handler_url_prefix, o.attrib["href"], suffix_url)

    def _manage_title(self, dom: etree._Element):
        if "hidetitle" in self.parameters and self.parameters["hidetitle"] == "true":
            h1s = xpath(dom, "//h1")
            if len(h1s) > 0:
                h1s[0].getparent().remove(h1s[0])

    def _replace_urls_process_links(self, dom: etree, attribute: str):
        # first find 'url' param to get the prefix website queried to display article content
        prefix_url = self.handler.get_original_website()
        for param in self.url[1:].split("&"):
            if param.startswith("url="):
                urlp = urlparse.urlparse(unquote(param.split("=")[1]))
                prefix_url = "%s://%s/" % (urlp.scheme, urlp.hostname)
                break

        for o in dom.xpath("//*[@%s]" % attribute):
            if o.attrib[attribute].startswith("//"):
                protocol: str = "http:"
                if prefix_url.find("https") > -1:
                    protocol = "https:"
                o.attrib[attribute] = protocol + o.attrib[attribute]
            elif o.attrib[attribute].startswith("/"):
                o.attrib[attribute] = prefix_url + o.attrib[attribute][1:]
            elif not o.attrib[attribute].startswith("http") and o.attrib[attribute].find("#") == -1:
                o.attrib[attribute] = prefix_url + o.attrib[attribute]
