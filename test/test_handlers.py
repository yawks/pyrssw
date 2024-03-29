import re

from lxml import etree
from requests.sessions import Session
from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler
from server.pyrssw_wsgi import HandlersManager


def test_handlers():

    for _, handler in HandlersManager.instance().get_handlers().items():
        print("Process: module : %s" % handler.__module__)

        py_rssw_request_handler: PyRSSWRequestHandler = handler()
        feed = py_rssw_request_handler.get_feed(
            {}, Session()).encode().decode('utf-8')
        
        dom = etree.fromstring(feed.encode("utf-8"))
        links = dom.xpath("//link")
        if len(links) <= 0:
            raise AssertionError
        py_rssw_request_handler.get_content(links[len(
            links)-1].text.replace("?url=", ""), {}, Session())  # test with last link of the feed
