import html
import json
import logging

import requests
from lxml import etree

import utils.dom_utils
import utils.json_utils
from handlers.launcher_handler import USER_AGENT
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class EurosportHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.eurosport.fr">Eurosport</a> website.

    Handler name: eurosport

    RSS parameters:
     - filter : tennis, football, rugby
       to invert filtering, prefix it with: ^
       eg :
         - /eurosport/rss?filter=tennis             #only feeds about tennis
         - /eurosport/rss?filter=football,tennis    #only feeds about football and tennis
         - /eurosport/rss?filter=^football,tennis   #all feeds but football and tennis

    Content:
        Content remains Eurosport links except for video pages.
        Video pages in the eurosport website are dynamically built using some javascript, the handler provide a simple page with a HTML5 video object embedding the video.
    """

    @staticmethod
    def get_handler_name() -> str:
        return "eurosport"

    def get_original_website(self) -> str:
        return "https://www.eurosport.fr/"

    def get_rss_url(self) -> str:
        return "https://www.eurosport.fr/rss.xml"

    def get_feed(self, parameters: dict) -> str:
        feed = requests.get(url=self.get_rss_url(), headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category, eg /eurosport/rss/tennis
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        # replace video links, they must be processed by getContent
        for link in dom.xpath("//link"):
            # if link.text.find("/video.shtml") > -1:
            link.text = "%s?url=%s" % (self.url_prefix, link.text)

        feed = etree.tostring(dom, encoding='unicode')

        return feed

    def _get_rss_link_description(self, link_url: str) -> str:
        """find in rss file the item having the link_url and returns the description"""
        description = ""
        feed = requests.get(url=self.get_rss_url(), headers={}).text
        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)
        descriptions = dom.xpath(
            "//item/link/text()[contains(., '%s')]/../../description" % link_url)
        if len(descriptions) > 0:
            description = html.unescape(descriptions[0].text)

        return description

    def get_content(self, url: str, parameters: dict) -> str:
        content = ""

        if url.find("/video.shtml") > -1 and url.find("_vid") > -1:
            content = self._get_video_content(url)
        else:
            content = self._get_content(url)

        return content

    def _get_content(self, url: str) -> str:
        content = requests.get(url, headers={"User-Agent": USER_AGENT}).text
        content = content.replace(">", ">\n")
        # in the majority of eurosport pages a json object contains all the content in tag with id __NEXT_DATA__
        idx = content.find("__NEXT_DATA__")
        if idx > -1:
            offset = content[idx:].find(">")
            end = content[idx+offset:].find("</script>")

            data = json.loads(content[idx+offset+1:idx+offset+end])
            articles = utils.json_utils.get_nodes_by_name(data, "article")
            for article in articles:
                if "publicationTime" in article:
                    content = ArticleBuilder(article).build_article()

        return content

    def _get_video_content(self, url: str) -> str:
        """ video in eurosport website are loaded using some javascript
            we build here a simplifed page with the rss.xml item description + a video object"""
        vid = url[url.find("_vid")+len("_vid"):]
        vid = vid[:vid.find('/')]
        page = requests.get(
            url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % vid, headers={"User-Agent": USER_AGENT})
        j = json.loads(page.text)

        return """
                    <div>
                        <p>
                            <a href="%s"><p>%s</p></a>
                            <video controls="" preload="auto">
                                <source src="%s" />
                            </video>
                        </p>
                        <p>%s</p>
                    </div>""" % (j["EmbedUrl"], j["Title"], j["VideoUrl"], self._get_rss_link_description(url[1:]))


class ArticleBuilder():
    """Uses the json produced by eurosport pages and build a simple html page parsing it.
    """

    def __init__(self, data: dict):
        self.data = data

    def build_article(self):
        content: str = "<html>"
        if "title" in self.data:
            content += "<h1>%s</h1>" % self.data["title"]
        if "picture" in self.data and "url" in ["picture"]:
            content += "<img %s src=\"%s\"/>" % (
                'width="100%"', self.data["picture"]["url"])
        content += self._build_content_from_json(self.data)
        content += "</html>"

        return content

    def _build_content_from_json(self, data) -> str:
        content: str = ""
        bodies = utils.json_utils.get_nodes_by_name(data, "body")
        if len(bodies) > 0:
            for entry in bodies[0]:
                if "node" in entry:
                    if entry["node"] == "paragraph":
                        content += self._build_entry("p", entry["content"])
                    elif entry["node"] == "blockquote":
                        content += self._build_entry("blockquote",
                                                     entry["content"])
                    elif entry["node"] == "h2":
                        content += self._build_entry("h2", entry["content"])
                    elif entry["node"] == "picture":
                        content += self._build_img(entry["content"])
                    elif entry["node"] == "video":
                        content += self._build_video(entry["content"])
                    else:
                        logging.getLogger().debug(
                            "Tag '%s' not handled" % entry["node"])

        return content

    def _build_video(self, content_dict: dict) -> str:
        content: str = ""

        if "databaseId" in content_dict:
            poster: str = ""
            if "picture" in content_dict and "url" in content_dict["picture"]:
                poster = content_dict["picture"]["url"]
            title: str = ""
            if "title" in content_dict:
                title = content_dict["title"]
            page = requests.get(
                url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % content_dict["databaseId"], headers={"User-Agent": USER_AGENT})
            j = json.loads(page.text)
            content = """<video controls="" preload="auto" poster="%s">
                                <source src="%s" />
                            </video><p><i><small>%s</small></i></p>""" % (poster, j["VideoUrl"], title)

        return content

    def _build_img(self, content_dict: dict) -> str:
        content: str = ""
        alt: str = ""
        if "caption" in content_dict:
            alt = " alt=\"%s\"" % content_dict["caption"]
        if "url" in content_dict:
            content += " src=\"%s\"%s" % (content_dict["url"], alt)

        return "<img %s %s/>" % ('width="100%"', content)

    def _build_entry(self, tag: str, content_list: list) -> str:  # NOSONAR
        content: str = "<%s>" % tag
        style: str = "%s"
        
        for entry in content_list:
            content += self._build_entry_content(tag, entry)
            
        return style % ("%s</%s>\n" % (content, tag))
    
    def _build_entry_content(self, tag, entry) -> str:
        content: str = ""
        style = self._get_style(entry)
        if "type" in entry:
            if entry["type"] == "text" and "content" in entry:
                if isinstance(entry["content"], list):
                    for c in entry["content"]:
                        content += self._build_entry_content(tag, c)
                else:
                    content += style % entry["content"]
            elif (entry["type"] == "hyperlink" or entry["type"] == "story") and "url" in entry and "label" in entry:
                content += style % "<a href=\"%s\">%s</a>" % (
                    entry["url"], entry["label"])
            elif entry["type"] == "internal" and "url" in entry:
                content += style % self._build_img(entry)

        return content

    def _get_style(self, content_dict: dict):
        style: str = "%s"
        if "style" in content_dict:
            for st in content_dict["style"]:
                if st == "bold":
                    style = style % "<b>%s</b>"
                elif st == "italic":
                    style = style % "<i>%s/</i>"

        return style
