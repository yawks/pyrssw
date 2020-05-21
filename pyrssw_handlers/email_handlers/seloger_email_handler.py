from typing import List, Optional

from lxml import etree
from urllib.parse import parse_qs
import urllib.parse as urlparse
from pyrssw_handlers.email_handlers.real_estate import Asset, Assets
from pyrssw_handlers.email_handlers.abstract_email_handler import AbstractEmailHandler


class SeLogerEmailHandler(AbstractEmailHandler):


    def process_message(self, msg):
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                self._process_html_message(str(part.get_payload(decode=True),
                                               "utf8").replace("\r\n", "\n"), msg["date"])

    def _process_html_message(self, html: str, date: str):
        dom = etree.HTML(html)

        a_imgs = dom.xpath("//a[contains(@_label, 'Image')]")
        prices = dom.xpath("//a[contains(@_label, 'Prix')]")
        a_descrs = dom.xpath("//a[contains(@_label, 'Description annonce')]")
        for a_img in a_imgs:
            url = a_img.attrib["href"]
            n_price = self._get_seloger_entry_by_url(prices, url)
            n_descr = self._get_seloger_entry_by_url(a_descrs, url)

            small_description: str = ""
            location: str = ""
            price: str = ""
            if not n_descr is None:
                small_description = " ".join(
                    n_descr.text.replace("\n", "").split())
                if len(n_descr.getchildren()) > 0:
                    location = n_descr.getchildren()[
                        0].tail.strip()
            if not n_price is None and len(n_price.getchildren()) > 0:
                price = n_price.getchildren()[0].text

            if price != "":
                self.assets.add_asset(Asset(
                    url=self._get_short_url(url),
                    small_description=small_description,
                    img_url=self._get_img_url(a_img),
                    price=price,
                    location=location,
                    email_date=date,
                    url_prefix=self.url_prefix,
                    handler="seloger"))

    def _get_img_url(self, a_img: etree._Element) -> str:
        img_url: str = ""
        for img in a_img.xpath(".//img"):
            if "src" in img.attrib:
                img_url = img.attrib["src"]
                break
        return img_url

    def _get_seloger_entry_by_url(self, a_nodes: List[etree._Element], url):
        node: Optional[etree._Element] = None
        parsed = urlparse.urlparse(url)
        if "idannali" in parse_qs(parsed.query):
            idannali = parse_qs(parsed.query)["idannali"]
            for a in a_nodes:
                if "href" in a.attrib:
                    parsed = urlparse.urlparse(a.attrib["href"])
                    if "idannali" in parse_qs(parsed.query) and idannali == parse_qs(parsed.query)["idannali"]:
                        node = a
                        break

        return node

    def _get_short_url(self, url):
        new_url = url
        parsed = urlparse.urlparse(url)
        if "p1" in parse_qs(parsed.query):
            new_url = "http://%s" % parse_qs(parsed.query)["p1"][0]
        return new_url
