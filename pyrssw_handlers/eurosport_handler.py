import html
import json
import logging
from base64 import b64decode
from request.pyrssw_content import PyRSSWContent
from typing import Dict, List, Optional, cast

import requests
from lxml import etree

import utils.dom_utils
from utils.dom_utils import to_string, xpath
from utils import json_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


CONTENT_MARKER = "#CONTENT#"


class EurosportHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.eurosport.fr">Eurosport</a> website.

    Handler name: eurosport

    RSS parameters:
     - filter : tennis, football, rugby
       to invert filtering, prefix it with: ^
       eg :
         - /eurosport/rss?filter=tennis             #only feeds about tennis
         #only feeds about football and tennis
         - /eurosport/rss?filter=football,tennis
         - /eurosport/rss?filter=^football,tennis   #all feeds but football and tennis

    Content:
        Content remains Eurosport links except for video pages.
        Video pages in the eurosport website are dynamically built using some javascript, the handler provide a simple page with a HTML5 video object embedding the video.
    """

    def get_original_website(self) -> str:
        return "https://www.eurosport.fr/"

    def get_rss_url(self) -> str:
        return "https://www.eurosport.fr/rss.xml"

    @staticmethod
    def get_favicon_url() -> str:
        return "https://layout.eurosport.com/i/sd/logo.jpg"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        feed = session.get(url=self.get_rss_url(), headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)

        if "filter" in parameters:
            # filter only on passed category, eg /eurosport/rss/tennis
            xpath_expression = utils.dom_utils.get_xpath_expression_for_filters(
                parameters, "category/text() = '%s'", "not(category/text() = '%s')")

            utils.dom_utils.delete_nodes(dom.xpath(xpath_expression))

        # replace video links, they must be processed by getContent
        for node in xpath(dom, "//link|//guid"):
            # if link.text.find("/video.shtml") > -1:
            node.text = "%s" % self.get_handler_url_with_parameters(
                {"url": cast(str, node.text)})

        feed = to_string(dom).replace("\\u0027", "'").replace("\\u0022", "'")

        return feed

    def _get_rss_link_description(self, link_url: str) -> str:
        """find in rss file the item having the link_url and returns the description"""
        description = ""
        feed = requests.get(url=self.get_rss_url(), headers={}).text
        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="utf-8"?>', '')
        dom = etree.fromstring(feed)
        descriptions = xpath(dom,
                             "//item/link/text()[contains(., '%s')]/../../description" % link_url)
        if len(descriptions) > 0:
            description = html.unescape(cast(str, descriptions[0].text))

        return description

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        content = ""

        if url.find("/video.shtml") > -1 and url.find("_vid") > -1:
            content = self._get_video_content(url, session)
        elif url.find("www.rugbyrama.fr") > -1:
            page = session.get(url=url)
            dom = etree.HTML(page.text)
            self._process_lazy_img(dom)
            utils.dom_utils.delete_xpaths(dom, [
                '//div[contains(@class, "storyfull__header")]',
                '//div[contains(@class, "storyfull__publisher-social-button")]',
                '//*[contains(@class, "outbrain-container")]',
                '//*[contains(@class, "related-stories")]',
                '//*[@id="header-sharing"]'])
            content = utils.dom_utils.get_content(dom, [
                '//div[contains(@class, "storyfull")]'])
        elif url.find("/live.shtml") > -1 or url.find("/liveevent.shtml") > -1:
            page = session.get(url=url)
            dom = etree.HTML(page.text)
            utils.dom_utils.delete_xpaths(dom, [
                '//*[@class="nav-tab"]',
                '//*[@class="live-match-nav__sharing"]',
                '//*[@class="livecomments-nav"]',
                '//*[@id="subnavigation-nav-tabs"]',
                '//*[contains(@class,"livecomments-header")]',
                '//*[contains(@class,"score-cards--hide-desktop-sm")]'
            ])
            self._process_lazy_img(dom)
            content = utils.dom_utils.get_content(dom, [
                '//div[@id="content"]',  # handles live scores
                '//section[@id="content"]',  # handles live scores
                '//*[@class="livecomments-content"]'  # handler live transfers
            ])

            content = utils.dom_utils.get_content(dom, [
                # add score if any
                '//*[contains(@class,"heromatch__col heromatch__col--center")]'
            ]) + content
        else:
            content = self._get_content(url, session)

        content = content.replace("width=\"100%\"", "style=\"width:100%\"")

        return PyRSSWContent(content, """
            # eurosport_handler .storyfull__ng-picture img {width:100%}
            # eurosport_handler .live-summary__seo-picture img {width:100%}
            # eurosport_handler .img-link img {
                float: none;
                display: block;
                margin: 0 auto;
            }

            # eurosport_handler .storyfull__publisher-time span::before {
                content: ' | ';
            }

            # eurosport_handler .heromatch__status {
                display: block;
            }

            # eurosport_handler .heromatch__col heromatch__col--center, #eurosport_handler .heromatch__score, #eurosport_handler  .heromatch__score-dash, #eurosport_handler .heromatch__score {
                display: inline-block;
            }

            # eurosport_handler img.livecomments-icon, #eurosport_handler img.isg-interchange {
                float:none;
            }
        """)

    def _get_content(self, url: str, session: requests.Session) -> str:
        content = session.get(url).text
        content = content.replace(">", ">\n")
        # in the majority of eurosport pages a json object contains all the content in tag with id __NEXT_DATA__
        idx = content.find("__NEXT_DATA__")
        if idx > -1:
            offset = content[idx:].find(">")
            end = content[idx+offset:].find("</script>")

            data = json.loads(content[idx+offset+1:idx+offset+end])

            ql_ref = self._get_ql_ref(data)
            if ql_ref is not None:
                content = QLArticleBuilder(data, ql_ref).build_article()
            else:
                articles = json_utils.get_nodes_by_name(data, "article")
                for article in articles:
                    if "publicationTime" in article:
                        content = ArticleBuilder(article).build_article()

        return content

    def _get_ql_ref(self, data: dict) -> Optional[str]:
        """Returns ql article ref if found

        Args:
            data (dict): data loaded in html page

        Returns:
            Optional[str]: ref article or None if not found
        """
        ql_ref: Optional[str] = None
        page_unique_ids = json_utils.get_nodes_by_name(
            data, "pageUniqueID")
        if len(page_unique_ids) == 1:
            client_roots = json_utils.get_nodes_by_name(
                data, "articleByDatabaseId(databaseId:%s)" % page_unique_ids[0])
            if len(client_roots) == 1:
                refs = json_utils.get_nodes_by_name(
                    client_roots[0], "__ref")
                if len(refs) > 0:
                    ql_ref = cast(str, refs[0])

        return ql_ref

    def _get_video_content(self, url: str, session: requests.Session) -> str:
        """ video in eurosport website are loaded using some javascript
            we build here a simplifed page with the rss.xml item description + a video object"""
        video_content: str = "<p>404 ?</p>"
        vid = url[url.find("_vid")+len("_vid"):]
        vid = vid[:vid.find('/')]

        page = session.get(
            url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % vid)
        j = json.loads(page.text)

        if "EmbedUrl" in j:
            embed: str = ""
            if "VideoUrl" in j:
                embed = """<video width="100%%" controls="" preload="auto" poster="%s">
                                    <source src="%s" />
                                </video>""" % (j["PictureUrl"] if "PictureUrl" in j else "", j["VideoUrl"])

            video_content = """
                    <div>
                        <p>
                            <a href="%s"><p>%s</p></a>
                            %s
                        </p>
                        <p>%s</p>
                    </div>""" % (j["EmbedUrl"],
                                 j["Title"],
                                 embed,
                                 self._get_rss_link_description(url[1:])
                                 .replace("\\u0027", "'")
                                 .replace("/>", "/><br/><br/>")
                                 .replace("<img", "<img width=\"100%\""))

        return video_content

    def _process_lazy_img(self, dom: etree._Element):
        for n in dom.xpath('//*[@data-lazy-type="img"]'):
            if "data-lazy" in n.attrib:
                img = etree.Element("img")
                img.attrib["src"] = n.attrib["data-lazy"]
                n.getparent().append(img)
                n.getparent().remove(n)

        for n in dom.xpath('//div[@data-img-interchange]/img'):
            try:
                data_img_interchange_json = json.loads(
                    n.getparent().attrib["data-img-interchange"])
                if "f" in data_img_interchange_json:
                    for size in data_img_interchange_json["f"]:
                        if "src" in data_img_interchange_json["f"][size]:
                            n.attrib["src"] = data_img_interchange_json["f"][size]["src"]
            except Exception as _:
                logging.getLogger().info("Unable to parse 'data-img-interchange'")


class ArticleBuilder():
    """Uses the json produced by eurosport pages and build a simple html page parsing it.
    """

    def __init__(self, data: dict):
        self.data = data

    def build_article(self):
        content: str = "<html>"
        if "title" in self.data:
            content += "<h1>%s</h1>" % self.data["title"]
        if "picture" in self.data and "url" in self.data["picture"]:
            content += "<img width=\"100%%\" src=\"%s\"/>" % self.data["picture"]["url"]
        content += self._build_content_from_json(self.data)
        content += "</html>"

        return content

    def _build_content_from_json(self, data) -> str:
        content: str = ""
        bodies = json_utils.get_nodes_by_name(data, "body")
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
                            "Tag '%s' not handled", entry["node"])

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
                url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % content_dict["databaseId"])
            j = json.loads(page.text)

            if poster == "" and "PictureUrl" in j:
                poster = j["PictureUrl"]

            if "VideoUrl" in j:
                content = """<video width="100%%" controls="" preload="auto" poster="%s">
                                    <source src="%s" />
                                </video>""" % (poster, j["VideoUrl"])
            elif "EmbedUrl" in j:
                content = """<iframe src="%s"/>""" % (j["EmbedUrl"])

            content += "<p><i><small>%s</small></i></p>" % title

        return content

    def _build_img(self, content_dict: dict) -> str:
        content: str = ""
        alt: str = ""
        if "caption" in content_dict:
            alt = " alt=\"%s\"" % content_dict["caption"]
        if "url" in content_dict:
            content += " src=\"%s\"%s" % (content_dict["url"], alt)

        return "<img width=\"100%%\" %s/>" % content

    def _build_entry(self, tag: str, content_list: list) -> str:  # NOSONAR
        content: str = "<%s>" % tag
        style: str = "%s"

        for entry in content_list:
            content += self._build_entry_content(tag, entry)

        return style % ("%s</%s>\n" % (content, tag))

    def _build_entry_content(self, tag, entry) -> str:  # NOSONAR
        content: str = ""
        style = self._get_style(entry)
        if "type" in entry:
            if entry["type"] == "text" and "content" in entry:
                if isinstance(entry["content"], list):
                    for c in entry["content"]:
                        content += self._build_entry_content(tag, c)
                else:
                    content += style % entry["content"]
            elif (entry["type"] == "hyperlink" or entry["type"] == "story" or entry["type"] == "external") and "url" in entry and "label" in entry:
                content += style % "<a href=\"%s\">%s</a>" % (
                    entry["url"], entry["label"])
            elif entry["type"] == "hyperlink" and "content" in entry:
                content += self._build_entry_content(tag, entry["content"])
            elif entry["type"] == "internal" and "url" in entry:
                content += style % self._build_img(entry)
            elif entry["type"] == "YouTube" and "url" in entry and "label" in entry:
                content += "<iframe class=\"pyrssw_youtube\" src=\"%s\">%s</iframe><p class=\"pyrssw_centered\"><i>%s</i></p>" % (
                    entry["url"], entry["label"], entry["label"])
            elif entry["type"] == "Twitter" and "url" in entry and "label" in entry:
                content += "<a href=\"%s\">%s/<a>" % (
                    entry["url"], entry["label"])
            else:
                logging.getLogger().debug(
                    "Entry type '%s' not (fully) handled", entry["type"])

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


class QLArticleBuilder():
    """New way to defined articles with GraphQL
    """

    def __init__(self, data: dict, ql_ref: str) -> None:
        self.data: dict = data
        self.root: Optional[dict] = json_utils.get_node(
            self.data, "props", "pageProps", "serverQueryRecords")
        if self.root is not None:
            #self.root = self.root[next(iter(self.root))]
            self.ql_article: dict = self.root[ql_ref]
            # self.ql_article: Optional[dict] = cast(Optional[dict], json_utils.get_first_node_in_subpath(
            #    data, ql_ref))
        self.graph_ql_body: Optional[str] = None

    def build_article(self) -> str:
        content: str = ""
        if self.ql_article is not None:
            if "title" in self.ql_article:
                content += "<h1>%s</h1>" % self.ql_article["title"]
            # picture_id = cast(str, json_utils.get_first_node_in_subpath(
            #    self.ql_article, "picture", "__ref"))
            picture_id = json_utils.get_node(
                cast(dict, self.ql_article), "picture", "__ref")
            if picture_id is not None:
                picture_node = json_utils.get_node(
                    cast(dict, self.root), cast(str, picture_id))
                if picture_node is not None:
                    content += "<img src=\"%s\"/>" % json_utils.get_node(
                        picture_node, "url")

            self.graph_ql_body = cast(str, json_utils.get_node(
                self.ql_article, "graphQLBody", "__ref"))
            if self.graph_ql_body is not None:
                content += self._build(self.graph_ql_body)

        return content

    def _build(self, node_name: str) -> str:
        content: str = ""

        node = cast(dict, json_utils.get_node(
            cast(dict, self.root), node_name))
        content_formatter: str = self._format(node)

        nodes_index = cast(Optional[List[str]], json_utils.get_node(
            cast(dict, self.root), node_name,  "contents", "__refs"))
        if isinstance(nodes_index, list):
            for node_index in nodes_index:
                refs_node_name = cast(str, json_utils.get_node(
                    cast(dict, self.root), node_index, "__id"))
                if refs_node_name is not None:
                    content += self._build(refs_node_name)

        return content_formatter.replace(CONTENT_MARKER, content)

    def _format(self, node: dict) -> str:
        type_name = cast(str, json_utils.get_node(node, "__typename"))
        node_format: str = "<p><i><small>Unknown type name: '%s'%s</small></i></p>" % (
            type_name, CONTENT_MARKER)  # default value if type name not handled

        if type_name == "HyperLink":
            node_format = "<a href=\"%s\">%s</a>" % (
                node["url"], CONTENT_MARKER)
        elif type_name == "Picture":
            node_format = "<img src=\"%s\" alt=\"%s\"></img>%s" % (
                node["url"],
                node["caption"],
                CONTENT_MARKER)
        elif type_name == "Video":
            node_format = self._format_video(node)
        elif type_name in ["Paragraph", "ListItem"]:
            node_format = "<p>%s</p>" % CONTENT_MARKER
        elif type_name == "Text":
            node_format = node["content"]
        elif type_name == "H2":
            node_format = "<h2>%s</h2>" % CONTENT_MARKER
        elif type_name == "HyperLinkInternal":
            node_format = "<a href=\"%s\">%s</a>" % (self._build(
                cast(str, json_utils.get_node(node, "content", "__ref"))),
                node["label"])
        elif type_name == "Link":
            node_format = node["url"]
        elif type_name == "InternalContent":
            node_format = self._build(
                cast(str, json_utils.get_node(node,  "content", "__ref")))
        elif type_name == "List":
            node_format = self._format_list(node)
        elif type_name == "Blockquote":
            node_format = "<blockquote>%s</blockquote>" % CONTENT_MARKER
        elif type_name in ["Body", "CyclingStage", "Program"]:
            node_format = CONTENT_MARKER
        elif type_name == "BreakLine":
            node_format = "<br/>"
        elif type_name in ["TeamSportsMatch", "Article"]:
            node_format = self._build(
                cast(str, json_utils.get_node(node, "link", "__ref")))
        elif type_name == "Table":
            node_format = self._format_table(node)
        elif type_name == "TableLine":
            node_format = self._format_table_line(node)
        elif type_name == "TableColumn":
            node_format = self._format_table_column(node)
        elif type_name == "Embed":
            node_format = self._format_embed(node)

        return node_format

    def _format_table_column(self, node: dict) -> str:
        tds = ""
        for td in cast(List[str], json_utils.get_node(node, "contents", "__refs")):
            tds = "\n\t<td>%s</td>" % self._build(td)

        return tds

    def _format_table_line(self, node: dict) -> str:
        tds = ""
        if "tableColumns" in node and "__refs" in node["tableColumns"]:
            for td in node["tableColumns"]["__refs"]:
                tds += cast(str, self._build(td))
        return "<tr>%s</tr>" % tds

    def _format_table(self, node: dict) -> str:
        trs = ""
        if "tableLines" in node and "__refs" in node["tableLines"]:
            for tr in node["tableLines"]["__refs"]:
                trs += cast(str, self._build(tr))
        return "<table>%s</table>" % trs

    def _format_embed(self, node: dict) -> str:
        content: str
        type_node: Optional[str] = node["type"]
        if type_node == "ACAST":
            content = "<a href=\"%s\">%s</a>" % (node["url"], node["label"])
        elif type_node == "TWITTER":
            content = "<p><a href=\"%s\">%s</a></p>" % (
                node["url"], node["label"])
        elif type_node in ["YOUTUBE", "DAILYMOTION"]:
            content = "<iframe width=\"560\" height=\"315\" src=\"%s\"></iframe>" % node["url"]
        elif type_node == "INSTAGRAM":
            content = "<iframe width=\"560\" height=\"315\" src=\"%sembed\"></iframe>" % node["url"].split("?")[
                0]
        else:
            content = "<p><i><small>Unknown embed type name: '%s'%s</small></i></p>" % (
                type_node, CONTENT_MARKER)

        return content

    def _format_list(self, node: dict) -> str:
        content: str = ""
        nodes_index: Optional[List[str]] = cast(Optional[List[str]], json_utils.get_node(
            node,  "listItems", "__refs"))
        if nodes_index is not None:
            for node_index in nodes_index:
                content += self._build(node_index)

        return content

    def _format_video(self, node: dict) -> str:
        content: str = ""

        if "id" not in node:
            link: Optional[str] = cast(
                Optional[str], json_utils.get_node(node, "link", "__ref"))
            if link is not None:
                content = self._build(link)
        else:
            video_id: str = b64decode(
                cast(str, node["id"]).encode("ascii")).decode("ascii")
            page = requests.get(
                url="https://www.eurosport.fr/cors/feed_player_video_vid%s.json" % video_id[len("Video:"):])
            j = json.loads(page.text)

            poster = ""
            if "PictureUrl" in j:
                poster = j["PictureUrl"]

            if "VideoUrl" in j:
                content = """<video width="100%%" controls="" preload="auto" poster="%s">
                                    <source src="%s" />
                                </video>""" % (poster, j["VideoUrl"])
            elif "EmbedUrl" in j:
                content = """<iframe src="%s"/>""" % (j["EmbedUrl"])

            content += "<p><i><small>%s</small></i></p>" % json_utils.get_node(
                node, "title")

        return content
