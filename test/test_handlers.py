import glob
import importlib
import inspect
import os
from lxml import etree
import re

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler

def test_handlers():
    handlers = glob.glob("pyrssw_handlers/*.py")
    assert len(handlers) > 0
    for handler in handlers:
        module_name = ".%s" % os.path.basename(handler).strip(".py")
        module = importlib.import_module(module_name, package="pyrssw_handlers")
        print("Process: module : %s" % module_name)
        if hasattr(module, "PyRSSWRequestHandler") and not hasattr(module, "ABC"):
            for member in inspect.getmembers(module):
                check_handler(member, module)
                

def check_handler(member, module):
    if member[0].find("__") == -1 and isinstance(member[1], type) and issubclass(member[1], getattr(module, "PyRSSWRequestHandler")) and member[1].__name__ != "PyRSSWRequestHandler":
        py_rssw_request_handler : PyRSSWRequestHandler = member[1]()
        feed = py_rssw_request_handler.get_feed({}).encode().decode('utf-8')
        # I probably do not use etree as I should
        feed = re.sub(r'<\?xml [^>]*?>', '', feed).strip()
        dom = etree.fromstring(feed)
        links = dom.xpath("//link")
        assert len(links) > 0
        py_rssw_request_handler.get_content(links[len(links)-1].text.replace("?url=", ""), {}) # test with last link of the feed

