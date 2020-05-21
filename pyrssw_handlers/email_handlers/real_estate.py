from typing import List, Optional


class Asset():
    """Represent an asset for real estate"""
    url: str = ""
    price: str = ""
    img_url: str = ""
    location: str = ""
    small_description: str = ""
    email_date: str = ""
    url_prefix: str = ""
    handler: str = ""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_item_feed(self):
        return """<item>
    <title>%s - %s - %s</title>
    <description>
        <img src="%s"/><p>%s - %s - %s</p>
        <p><b><i>%s</i></b></p>
    </description>
    <link>
        %s%s?url=%s
    </link>
    <pubDate>%s</pubDate>
</item>""" % (self.location, self.price, self.small_description,
              self.img_url, self.location, self.price, self.small_description,
              self.handler,
              self.url_prefix, self.handler, self.url,
              self.email_date)


class Assets():
    """List of real estate assets"""
    asset_list: List[Asset] = list()

    def add_asset(self, asset: Asset):
        """Add an asset to the list
        If the asset already exists, the properties set of given asset are used to update existing asset.

        Arguments:
            asset {Asset} -- Asset to add
        """
        existing_asset: Optional[Asset] = None
        for a in self.asset_list:
            if a.url == asset.url:
                existing_asset = a
                break
        if existing_asset is None:
            self.asset_list.append(asset)
        else:
            items = vars(asset).items()
            for item in items:
                #print (item[0])
                if item[1] != "" and not item[1] is None:
                    existing_asset.__dict__[item[0]] = item[1]

    def to_rss_feed(self) -> str:
        rss_feed: str = """<rss version="2.0">
    <channel>
        <title>Se Loger</title>
        <language>fr-FR</language>
        %s
    </channel>
</rss>
"""
        items: str = ""
        for asset in self.asset_list:
            items += asset.to_item_feed()

        return rss_feed % items
