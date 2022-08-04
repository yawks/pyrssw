from request.pyrssw_content import PyRSSWContent
from datetime import datetime
import string
import re
from typing import Dict, cast
import requests
from lxml import etree
import json
from pyrssw_handlers.abstract_pyrssw_request_handler import PyRSSWRequestHandler
from utils.dom_utils import delete_xpaths, get_content, text, to_string, xpath

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"


class LequipeHandler(PyRSSWRequestHandler):
    """Handler for french <a href="https://www.lequipe.fr">L'equipe</a> website.

    Handler name: lequipe

    RSS parameters:
     - filter : tennis, football, rugby, basket, cyclisme, football-transfert, jeux-olympiques, voile, handball, golf
       to invert filtering, prefix it with: ^
       eg :
         - /lequipe/rss?filter=tennis             #only feeds about tennis
         #only feeds about football and tennis
         - /lequipe/rss?filter=football,tennis
         - /lequipe/rss?filter=^football,tennis   #all feeds but football and tennis

    Content:
        Content without menus, ads, ...
    """

    def get_original_website(self) -> str:
        return "https://www.lequipe.fr/"

    def get_rss_url(self) -> str:
        return "https://www6.lequipe.fr/rss/actu_rss%s.xml"

    @staticmethod
    def get_favicon_url(parameters: Dict[str, str]) -> str:
        return "https://www.lequipe.fr/img/favicons/favicon.svg"

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        if parameters.get("filter") in ["tennis", "football", "rugby", "cyclisme", "golf", "basket", "jeux-olympiques", "voile", "handball", "formule-1", "football-transfert"]:
            # filter only on passed category, eg /lequipe/rss/tennis
            feed = session.get(url=self.get_rss_url() %
                               "_"+parameters["filter"].capitalize(), headers={}).text

            html = session.get(self.get_original_website(
            ) + parameters["filter"].capitalize(), headers={}).text

        else:
            feed = session.get(url=self.get_rss_url() %
                               "", headers={}).text
            html = session.get(self.get_original_website(), headers={}).text

        # I probably do not use etree as I should
        feed = feed.replace('<?xml version="1.0" encoding="UTF-8" ?>', '')
        regex = re.compile(r"&(?!amp;|lt;|gt;)")
        myxml = regex.sub("&amp;", feed)
        dom = etree.fromstring(myxml)
        description_img: str = ""

        links = []
        for link in xpath(dom, "//item/link"):
            if link is not None and text(link) is not None:
                href = text(link).strip().replace("#xtor=RSS-1", "")
                links.append(href)
                link.text = self.get_handler_url_with_parameters(
                    {"url": href})

        html_dom = etree.HTML(html)
        channel = xpath(dom, "//channel")[0]
        for article in xpath(html_dom, "//article/a"):
            #print(article.attrib["href"] + " " + xpath(article, ".//h2")[0].strip())
            href = article.attrib["href"]
            if href not in links and not href.startswith("https://bit.ly"):
                item = etree.Element("item")
                link = etree.Element("link")
                enclosure = etree.Element("enclosure")
                #description = etree.Element("description")
                title = etree.Element("title")
                pub_date = etree.Element("pubDate")

                link.text = self.get_handler_url_with_parameters(
                    {"url": href})

                title_str = ""
                images = xpath(
                    article, './/img[contains(@class,"Image__img")]')
                if len(images) > 0:
                    enclosure.attrib["url"] = images[0].attrib.get("src", "")
                    if len(images[0].attrib.get("alt", "")) > 0:
                        title_str = images[0].attrib.get("alt", "")

                titles = xpath(article, ".//h2")
                if len(titles) > 0:
                    title_str = text(titles[0]).strip()

                if title_str != "":
                    title.text = title_str
                    pub_date.text = datetime.now().strftime("%c")

                    item.append(link)
                    item.append(enclosure)
                    # item.append(description)
                    item.append(title)
                    item.append(pub_date)

                    channel.append(item)

        feed = to_string(dom)

        title = ""
        if "filter" in parameters:
            title = " - " + parameters["filter"]

        feed = feed.replace("<title>lequipe - Toute l'actualite</title>",
                            "<title>lequipe%s</title>" % string.capwords(title))

        if description_img != "":
            feed = feed.replace(
                "<description>", "<description>" + description_img)

        return feed

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> PyRSSWContent:
        page = session.get(url=url, headers={
                           "User-Agent": USER_AGENT, "sec-ch-ua-platform": "Windows"})

        content = page.text
        dom = etree.HTML(content, parser=None)
        delete_xpaths(dom, [
            '//div[@class="article__action"]',
            '//*[contains(@class,"RelatedLinks")]',
            '//*[contains(@aria-label,"Colonne de droite")]'
        ])

        json_content = _parse_article_object(dom, content)

        _remove_duplicate_imgs(dom)
        _move_header_img(dom)
        _process_video(dom)
        _process_instagram(dom)

        content = get_content(dom, [
            '//div[@class="article"]',
            '//*[contains(@class,"Sheet__content")]'
        ])
        content = content.replace("#JSONCONTENT#", json_content)
        content += """<style type="text/css">
@font-face {
    font-family: "DINNextLTPro-MediumCond";
    src: url(https://www.lequipe.fr/_fonts/DINNextLTPro-MediumCond.woff2) format("truetype");
}

@font-face {
    font-family: "DINNextLTPro-Regular";
    src: url(https://www.lequipe.fr/_fonts/DINNextLTPro-Regular.woff2) format("truetype");
}

</style>
        """

        return PyRSSWContent(content, """
            .Image__content {
  padding-top: 0 !important;
}

.Author__name {
  font-weight: 400;
}

.ArticleTags {
  font-family: 'DINNextLTPro-MediumCond', sans-serif;
  font-size: 20px;
  line-height: 18px;
  font-weight: 400;
  display: flex;
  flex-wrap: nowrap;
  align-items: baseline;
}

.ArticleTags__items {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #575756;
  color: var(--color-grey2-original, #575756);
}

.ArticleTags {
  font-family: 'DINNextLTPro-MediumCond', sans-serif;
  font-size: 16px;
  line-height: 18px;
  font-weight: 400;
  display: flex;
  flex-wrap: nowrap;
  align-items: baseline;
}

.ArticleTags__item.has-background {
  /*background-color: #ddd;
  background-color: var(--color-grey10-original, #ddd);
  color: #1d1d1b;
  color: var(--color-grey1-original, #1d1d1b);*/
  height: 22px;
  line-height: 22px;
  margin-left: 0;
  padding: 2px 6px 0;
  box-sizing: border-box;
  display: inline-block;
}

ArticleTags__items + .ArticleTags__paid {
  display: inline-block;
  margin-left: 6px;
  font-size: 16px;
}
.ArticleTags__paid {
  white-space: nowrap;
}

.flag {
  display: inline-block;
  box-sizing: border-box;
  font-family: 'DINNextLTPro-MediumCond', sans-serif;
  font-size: 15px;
  line-height: 19px;
  font-weight: 400;
  padding: 2px 5px 0;
  text-align: center;
  text-decoration: none;
  /*background-color: #1d1d1b;
  background-color: var(--color-black, #1d1d1b);
  color: #fff;
  color: var(--color-white, #fff);*/
}

.flag--small {
  font-size: 12px;
  line-height: 13px;
  padding: 2px 2px 0 3px;
}

.flag--bronze {
  color: #c4a749;
  color: var(--color-bronze, #c4a749);
  background-color: transparent;
  padding: 1px 0 0;
}

.ArticleTags__item.has-background + .ArticleTags__item:not(.has-background) {
  margin-left: 2px;
}
@media (min-width: 928px) .ArticleTags__item {
  margin-left: 3px;
}
.ArticleTags__item {
  display: inline;
  margin-left: 2px;
}

.ArticleTags__items + .ArticleTags__paid {
  display: inline-block;
  margin-left: 6px;
  font-size: 16px;
}

.Image__legend,
.Article__publishDate,
.Article__publishUpdateDate {
  font-family: 'DINNextLTPro-Regular', sans-serif;
  font-size: 14px;
  line-height: 20px;
  font-weight: 400;
  padding: 8px 0 0;
  color: #909090;
  color: var(--color-grey7, #909090);
}

.Article__publication {
  padding-top: 20px;
}

span.Article__publishDate::after {
  white-space: pre;
  content: '\A';
}

.Sheet__iframe {
  display: none;
}
.Sheet__content {
  font-family: 'DINNextLTPro-Regular', sans-serif;
  font-size: 16px;
  line-height: 16px;
  font-weight: 400;
  /*color: #1d1d1b;
  color: var(--color-black, #1d1d1b);*/
  padding: 24px 24px 0;
  overflow: hidden;
}
@media (min-width: 768px) {
  .Sheet__content {
    padding: 0;
  }
}
.Sheet__content h1 {
  font-family: 'DINNextLTPro-Bold', sans-serif;
  font-size: 24px;
  line-height: 24px;
  font-weight: 400;
  margin: 0 0 16px;
}
.Sheet__content h2 {
  font-size: 16px;
  line-height: 16px;
  margin: 0;
}
.Sheet__content a {
  color: #3873b8;
  color: var(--color-blue, #3873b8);
}
.Sheet__content a strong {
  font-weight: 500;
}
.Sheet__content a.link {
  font-family: 'DINNextLTPro-Regular', sans-serif;
  font-size: 16px;
  line-height: 16px;
  font-weight: 400;
  white-space: normal;
}
.Sheet__content .category-expand-list td:not(.competition):not(.nom) a {
  /*color: #1d1d1b;
  color: var(--color-black, #1d1d1b);*/
}
.Sheet__content table {
  width: 100%;
  margin-bottom: 10px;
}
.Sheet__content table.no-border tr {
  border: none;
}
.Sheet__content td {
  padding: 12px 10px 12px 0;
  vertical-align: bottom;
}
.Sheet__content td:first-child {
  padding-left: 5px;
}
.Sheet__content td:last-child {
  padding-right: 0;
}
.Sheet__content td strong:not(:last-child) {
  display: inline-block;
  margin-bottom: 4px;
}
.Sheet__content td img.flag {
  margin-right: 4px;
}
.Sheet__content td img.flag.drapeau {
  position: relative;
  top: 2px;
  width: 18px;
  height: 12px;
}
.Sheet__content tr {
  border-color: #ddd;
  border-left-color: var(--color-grey3, #ddd);
  border-bottom: 1px solid #ddd;
  border-bottom-color: var(--color-grey3, #ddd);
  border-right-color: var(--color-grey3, #ddd);
  border-top-color: var(--color-grey3, #ddd);
}
.Sheet__content tr.separateur-poste td {
  border-color: #1d1d1b;
  border-color: var(--color-black, #1d1d1b);
  border-top: 1px solid #1d1d1b;
  border-top-color: var(--color-black, #1d1d1b);
}
.Sheet__content th {
  padding: 12px 5px 12px 10px;
  font-weight: 400;
}
.Sheet__content th:first-child {
  padding-left: 0;
}
.Sheet__content th:last-child {
  padding-right: 0;
}
.Sheet__content img {
  display: inline-block;
  max-width: 100%;
  height: auto;
}
.Sheet__content img.drapeau {
  width: 18px;
  height: 12px;
  margin-right: 4px;
}
.Sheet__content img.evolFIFA {
  width: 18px;
  vertical-align: middle;
}
.Sheet__content figure {
  margin: 0;
}
.Sheet__content .visuel,
.Sheet__content .visuels-club {
  position: absolute;
  right: 24px;
  top: 12px;
  width: 120px;
}
.Sheet__content .visuel {
  max-width: 20%;
  top: 24px;
}
.Sheet__content .visuel figcaption {
  font-size: 0.9em;
  color: #596374;
  padding-top: 5px;
  position: absolute;
  left: -10%;
  width: 120%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.Sheet__content .informationEquipe {
  max-width: calc(100% - 124px);
}
.Sheet__content .informationEquipe figure {
  display: flex;
  margin-bottom: 8px;
  align-items: center;
  line-height: 23px;
}
.Sheet__content .informationEquipe img {
  width: 24px;
  height: 24px;
  margin-right: 8px;
}
.Sheet__content .informationEquipe ~ .identite {
  max-width: 100%;
}
.Sheet__content .informationEquipe ~ .identite td * {
  font-weight: 500;
}
.Sheet__content .identite {
  max-width: 75%;
  margin-bottom: 24px;
}
@media (min-width: 768px) {
  .Sheet__content .identite {
    max-width: calc(100% - 124px);
  }
}
.Sheet__content .identite td {
  width: 50%;
}
.Sheet__content .identite tr {
  border: none;
}
.Sheet__content .identite tr:not(:first-child) strong {
  font-weight: 500;
}
.Sheet__content .effectifclub th {
  text-align: left;
}
.Sheet__content .effectifclub td {
  padding-right: 5px;
}
.Sheet__content .effectifclub td:not(:first-child) {
  padding-left: 5px;
}
.Sheet__content .effectifclub td.numero {
  text-align: right;
}
.Sheet__content .effectifclub td.pays {
  min-width: 60px;
}
.Sheet__content .calendrierclub strong {
  font-weight: 500;
}
.Sheet__content .calendrierclub td {
  padding: 8px 2px;
  vertical-align: middle;
}
.Sheet__content .calendrierclub .score {
  min-width: 48px;
  text-align: center;
}
.Sheet__content .calendrierclub .equipe {
  width: 20%;
}
.Sheet__content .calendrierclub .equipe1 {
  text-align: right;
}
.Sheet__content .club img {
  width: 20px;
  margin-right: 2px;
  display: inline-block;
  vertical-align: middle;
}
.Sheet__content .Carriere th {
  font-weight: 400;
}
.Sheet__content .Carriere td,
.Sheet__content .Carriere th {
  width: auto;
  text-align: center;
  vertical-align: middle;
}
.Sheet__content .Carriere .club {
  text-align: left;
  padding-left: 5px;
}
.Sheet__content .Carriere .detail,
.Sheet__content .Carriere .soustitre {
  font-size: 0.625rem;
}
.Sheet__content .titre-barre {
  /*background: #ddd;
  background: var(--color-grey3, #ddd);*/
  font-family: 'DINNextLTPro-MediumCond', sans-serif;
  font-size: 18px;
  line-height: 42px;
  font-weight: 400;
  height: 40px;
  margin: 0 -24px;
  padding: 0 24px;
  position: relative;
  cursor: pointer;
}
@media (min-width: 768px) {
  .Sheet__content .titre-barre {
    margin: 0;
  }
}
.Sheet__content .titre-ss-barre,
.Sheet__content .titre-ss-barre-davis {
  font-family: 'DINNextLTPro-Bold', sans-serif;
  font-size: 18px;
  line-height: 50px;
  font-weight: 400;
  height: 50px;
}
.Sheet__content .category-expand:not(.close):after {
  transform: rotate(0);
}
.Sheet__content .category-expand:after {
  content: '';
  font-family: 'icons-ui';
  color: #909090;
  color: var(--color-grey7, #909090);
  position: absolute;
  display: inline-block;
  top: 0;
  right: 24px;
  width: 16px;
  transform: rotate(180deg);
}
.Sheet__content .close + .category-expand-list {
  margin-bottom: 24px;
}
.Sheet__content .close + .category-expand-list,
.Sheet__content .close + section {
  height: 0;
  overflow: hidden;
}



        """)


def _remove_duplicate_imgs(dom: etree._Element):
    alts = []
    for img in xpath(dom, "//img"):
        if "alt" in img.attrib:
            if img.attrib["alt"] in alts:
                img.getparent().remove(img)
            else:
                alts.append(img.attrib["alt"])


def _move_header_img(dom: etree._Element):
    for header in xpath(dom, '//*[contains(@class,"article__head")]'):
        for divimg in xpath(header, './/div[contains(@class,"Article__image")]'):
            header.append(divimg)
            # divimg.getparent().remove(divimg)


def _parse_article_object(dom: etree._Element, content: str) -> str:
    json_content = ""
    if content.find("articleObject:") > -1 and content.find('class="Article__paywall"') > -1:
        json_str = content.split("articleObject:")[1].split(
            ',articleType')[0].replace("\\u002F", "/")
        # u rl_nuxt = content.split('comment_count_url:"')[1].split('",')[0].replace("\\u002F", "/")
        json_str = re.sub(
            r"keywords:\[([\w\,\$]+)\]", "keywords:\"\"", json_str)
        json_str = re.sub(r"([{,])([a-zA-Z_]+\d?):",
                          r'\1"\2":', json_str)  # add quotes for key
        # add quotes for values
        json_str = re.sub(
            r":([a-zA-Z_]+\d*\$?)([},])", r':"\1"\2', json_str)
        # add quotes for numeric values
        json_str = re.sub(r"\":(\.?\d+)([},])", r'":"\1"\2', json_str)
        # add quotes for $ alone
        json_str = re.sub(r"\":\$([},])", r'":"$"\1', json_str)
        # add quotes for first value in array
        json_str = re.sub(
            r":\[([a-zA-Z_]+\d?\$?)([,\]])", r':["\1"\2', json_str)
        # add quotes for last value in array
        json_str = re.sub(
            r",([a-zA-Z_]+\d?\$?)\]", r',"\1"]', json_str)
        json_str = re.sub(r"([{,])([a-zA-Z_]+\d?):", r'\1"\2":', json_str)
        json_str = re.sub(r"},([\w]+),{", r'},"\1",{', json_str)
        json_json = json.loads(json_str)
        for item in json_json.get("items", []):
            if "objet" in item:
                for paragraph in item["objet"].get("paragraphs", []):
                    if type(paragraph) == dict:
                        if len(paragraph.get("title", "")) > 2:
                            title = paragraph["title"]
                            json_content += f"<p><strong>{title}</strong></p>"
                        if len(paragraph.get("content", "")) > 2:
                            pcontent = paragraph["content"].replace("\u003E", '>').replace(
                                "\u002F", '/').replace("\"", '"').replace('(^\"|\"$)"', '').replace("\t", '').replace("class=\" ", "")
                            json_content += f"<p>{pcontent}</p>"
                        if "media" in paragraph:
                            if "url" in paragraph["media"] and "ratio" in paragraph["media"]:
                                ratio = 1.5
                                if type(paragraph["media"]["ratio"]) == float:
                                    ratio = paragraph["media"]["ratio"]
                                url = paragraph["media"]["url"].replace("\u002F", '/').replace(
                                    '{width}', '800').replace('{height}', str(int(800 / ratio))).replace('{quality}', '75')
                                json_content += '<img src="' + url + '"</img>'
                            if "legende" in paragraph["media"] and "length" in paragraph["media"]["legende"]:
                                json_content += '<p><strong>' + \
                                    paragraph["media"]["legende"] + \
                                    '</strong></p>'

        article_body = xpath(dom, "//*[@class='article__body']")
        if len(article_body) > 0:
            new_article_body = etree.Element("div")
            new_article_body.attrib["class"] = "article__body"
            new_article_body.text = "#JSONCONTENT#"
            parent = article_body[0].getparent()
            parent.remove(article_body[0])
            parent.append(new_article_body)

    return json_content


def _process_video(dom: etree._Element):
    for divvideo in xpath(dom, '//*[contains(@class,"DmVideoEmbed")]'):
        for script in xpath(divvideo, ".//script"):
            script_str = cast(str, script.text)
            if script_str.find("VideoObject") > -1:
                jsonjson = json.loads(script_str)
                if jsonjson.get("EmbedUrl", "").find("dailymotion") > -1:
                    iframe = etree.Element("iframe")
                    iframe.attrib["class"] = "pyrssw_youtube"
                    iframe.attrib["src"] = jsonjson.get("EmbedUrl", "")
                    divvideo.append(iframe)
                else:
                    video = etree.Element("video")
                    video.set("controls", "")
                    video.set("preload", "auto")
                    video.set(
                        "poster", jsonjson.get("ThumbnailUrl", ""))
                    video.set("width", "100%")

                    source = etree.Element("source")
                    source.set("src", jsonjson.get("EmbedUrl", ""))

                    video.append(source)
                    divvideo.append(video)

                p = etree.Element("p")
                p.attrib["class"] = "Image__legend"
                p.text = jsonjson.get("Description", "")
                divvideo.append(p)


def _process_instagram(dom: etree._Element):
    for node in xpath(dom, '//*[@data-instgrm-permalink]'):
        if "data-instgrm-permalink" in node.attrib:
            node.attrib["data-instgrm-permalink"] += "&dark=true"
