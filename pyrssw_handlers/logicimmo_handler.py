from urllib.parse import unquote_plus

import requests
from lxml import etree

import utils.dom_utils
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class LogicImmoHandler(PyRSSWRequestHandler):
    """Handler for LogicImmo, french real estate website

    Handler name: logicimmo

    RSS parameters:
     - criteria : create a query in the logicimmo website, and in the page of results, copy all the content after the question mark, ie :
        https://www.logic-immo.com/vente-immobilier-paris-75,100_1/options/groupprptypesids=1,2,6,7,12,15/pricemin=200000/pricemax=400000

        copy this part:
          vente-immobilier-paris-75,100_1/options/groupprptypesids=1,2,6,7,12,15/pricemin=200000/pricemax=400000
        and then url encode it, the parameter becomes:
          criteria=vente-immobilier-paris-75%2C100_1%2Foptions%2Fgroupprptypesids%3D1%2C2%2C6%2C7%2C12%2C15%2Fpricemin%3D200000%2Fpricemax%3D400000
    """

    @staticmethod
    def get_handler_name() -> str:
        return "logicimmo"

    def get_original_website(self) -> str:
        return "https://www.logic-immo.com/"

    def get_rss_url(self) -> str:
        return ""

    def get_feed(self, parameters: dict, session: requests.Session) -> str:
        items: str = ""
        if "criteria" in parameters:
            url = "%s%s" % (
                self.get_original_website(), unquote_plus(parameters["criteria"]))
            page = requests.get(url=url) # for some reasons logicimmo website does not work with sessions
            dom = etree.HTML(page.text)
            for card in dom.xpath("//div[contains(@class,\"offer-list-item\")]"):

                location: str = self._get_location(card)
                price: str = self._get_price(card)
                img_url: str = self._get_img_url(card)

                small_description: str = "%sm² - %sp - %sch" % (
                    utils.dom_utils.get_text(
                        card, [".//span[contains(@class, \"offer-area-number\")]"]),
                    utils.dom_utils.get_text(card, [
                                             ".//span[contains(@class, \"offer-details-caracteristik--rooms\")]//span[contains(@class,\"offer-rooms-number\")]"]),
                    utils.dom_utils.get_text(card, [
                                             ".//span[contains(@class, \"offer-details-caracteristik--bedrooms\")]//span[contains(@class,\"offer-rooms-number\")]"])
                )

                url_detail: str = self._get_url(card)

                if small_description != "" and price != "":
                    items += """<item>
            <title>%s - %s - %s</title>
            <description>
                <img src="%s"/><p>%s - %s - %s</p>
            </description>
            <link>
                %s
            </link>
        </item>""" % (location, price, small_description,
                      img_url, location, price, small_description,
                      self.get_handler_url_with_parameters({"url": url_detail}))

        return """<rss version="2.0">
    <channel>
        <title>Logic Immo</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>""" % items

    def _get_location(self, card: etree.HTML) -> str:
        location: str = ""
        for span in card.xpath(".//span[contains(@class, \"offer-details-location--locality\")]"):
            location = span.text.strip()
            break

        for a in card.xpath(".//a[contains(@class,\"offer-details-location--sector\")]"):
            if "title" in a.attrib:
                location += " - " + a.attrib["title"]
                break

        return location

    def _get_price(self, card: etree.HTML) -> str:
        price: str = ""
        for node in card.xpath(".//p[contains(@class, \"offer-price\")]/span"):
            price = node.text.strip()
            break

        return price

    def _get_img_url(self, card: etree.HTML) -> str:
        img_url: str = ""
        for node in card.xpath(".//img[@data-original]"):
            img_url = node.attrib["data-original"]
            break

        return img_url

    def _get_url(self, card: etree.HTML) -> str:
        url_detail: str = ""
        for node in card.xpath(".//*[contains(@class, \"offer-link\")]"):
            if "href" in node.attrib:
                url_detail = node.attrib["href"]
                break

        return url_detail

    def get_content(self, url: str, parameters: dict, session: requests.Session) -> str:
        content: str = ""

        # for some reasons logicimmo website does not work with sessions
        page = requests.get(url=url)

        dom = etree.HTML(page.text)
        if dom is not None:

            descriptions = dom.xpath(
                "//div[@class=\"offer-description-text\"]")
            if len(descriptions) > 0:
                # move images to a readable node
                node = descriptions[0]
                cpt = 1
                for img in dom.xpath("//img[contains(@src,'182x136')]"):
                    new_img = etree.Element("img")
                    new_img.attrib["src"] = img.attrib["src"].replace(
                        "182x136", "800x600")
                    new_img.attrib["alt"] = "Images #%d" % cpt

                    node.append(new_img)
                    node.append(etree.Element("br"))
                    node.append(etree.Element("br"))
                    cpt = cpt + 1

            for node in dom.xpath("//*[contains(@class,\"carousel-wrapper\")]"):
                node.getparent().remove(node)

            utils.dom_utils.delete_xpaths(dom, [
                '//*[@id="photo"]',
                '//button'
            ])

            # remove orignal nodes containing photos
            content = utils.dom_utils.get_content(
                dom, ['//*[contains(@class, "offer-block")]']).replace("182x136", "800x600")
            content += utils.dom_utils.get_content(
                dom, ['//*[contains(@class, "offer-description")]'])

        return """
    <div class=\"main-content\">
        %s
    </div>""" % (content)