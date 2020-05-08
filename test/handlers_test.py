import glob
import importlib
import inspect
import logging
import os
import sys
import unittest
from typing import Type

from pyrssw_handlers.abstract_pyrssw_request_handler import \
    PyRSSWRequestHandler


class HandlersTest(unittest.TestCase):
    """Process a call of getFeed, getContent and getContentType for every custom handler"""

    def test_handlers(self): #NOSONAR
        log = logging.getLogger("TestLog")
        handlers = glob.glob("pyrssw_handlers/*.py")
        self.assertGreater(len(handlers), 0)
        for handler in handlers:
            module_name = ".%s" % os.path.basename(handler).strip(".py")
            module = importlib.import_module(module_name, package="pyrssw_handlers")
            log.debug("Process module : %s" % module_name)
            if hasattr(module, "PyRSSWRequestHandler") and not hasattr(module, "ABC"):
                for member in inspect.getmembers(module):
                    if member[0].find("__") == -1 and isinstance(member[1], type) and issubclass(member[1], getattr(module, "PyRSSWRequestHandler")) and member[1].__name__ != "PyRSSWRequestHandler":
                        py_rssw_request_handler : PyRSSWRequestHandler = module.PyRSSWRequestHandler("") #type: ignore
                        feed = py_rssw_request_handler.get_feed({}).encode().decode('utf-8')
                        self.assertIsNotNone(feed)
                        self.assertRegex(feed, ".*<channel.*")
                        content = py_rssw_request_handler.get_content("http://www.google.Fr", {}) # test with dummy url, just to check there is no exception raised
                        self.assertIsNotNone(content)
                        self.assertRegex(content, ".*<html.*")

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    unittest.TextTestRunner().run(HandlersTest())
