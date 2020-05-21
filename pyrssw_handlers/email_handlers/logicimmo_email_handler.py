from lxml import etree

from pyrssw_handlers.email_handlers.abstract_email_handler import \
    AbstractEmailHandler
from pyrssw_handlers.email_handlers.real_estate import Asset, Assets


class LogicImmoEmailHandler(AbstractEmailHandler):


    def process_message(self, msg):
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                self._process_html_message(str(part.get_payload(decode=True),
                                               "utf8").replace("\r\n", "\n"), msg["date"])

    def _process_html_message(self, html: str, date: str):  # TODO luxresidence
        dom = etree.HTML(html)

        img_url: str = ""
        price: str = ""
        location: str = ""
        small_description: str = ""

        for a in dom.xpath("//a[contains(@href,\"https://www.logic-immo.com/detail-vente-\")]"):
            url: str = a.attrib["href"].split("?")[0]
            # and "style" in a.getparent().attrib:
            if a.getparent().tag == "td" and "background" in a.getparent().attrib:
                img_url = a.getparent().attrib["background"]
                #m = re.search(r"background-image:\s*url\('([^'])+'\)", a.getparent().attrib["style"])
                # if not m is None:
                #    img_url = m.group(1)
            if a.attrib["href"].find("description_surface") > -1:
                small_description = a.text.strip()
            if a.attrib["href"].find("description_prix") > -1:
                price = a.text.strip()
            if a.attrib["href"].find("description_ville") > -1:
                location = a.text.strip()

            self.assets.add_asset(Asset(
                url=url,
                small_description=small_description,
                img_url=img_url,
                price=price,
                location=location,
                email_date=date,
                url_prefix=self.url_prefix,
                handler="logicimmo"))
