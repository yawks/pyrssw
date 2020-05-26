import re

from lxml import etree

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from server.pyrssw_wsgi import HandlersManager


def test_handlers():

    for handler in HandlersManager.instance().get_handlers():
        print("Process: module : %s" % handler.__module__)
        
        py_rssw_request_handler : PyRSSWRequestHandler = handler()
        feed = py_rssw_request_handler.get_feed({}).encode().decode('utf-8')
        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)
        links = dom.xpath("//link")
        if len(links) <= 0:
            raise AssertionError
        py_rssw_request_handler.get_content(links[len(links)-1].text.replace("?url=", ""), {}) # test with last link of the feed
