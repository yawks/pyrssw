from response.LeMondeHandler import PyRSSWRequestHandler
import unittest
import importlib
import glob
import os
import logging
import sys
from typing import Type

class HandlersTest(unittest.TestCase):
    """Process a call of getFeed, getContent and getContentType for every custom handler"""

    def test_handlers(self):
        log = logging.getLogger("TestLog")
        handlers = glob.glob("response/*Handler.py")
        self.assertGreater(len(handlers), 0)
        for handler in handlers:
            module_name = ".%s" % os.path.basename(handler).strip(".py")
            module = importlib.import_module(module_name, package="response")
            log.debug("Process module : %s" % module_name)
            if hasattr(module, 'PyRSSWRequestHandler'):
                py_rssw_request_hander : PyRSSWRequestHandler = module.PyRSSWRequestHandler("")
                feed = py_rssw_request_hander.get_feed({}).encode().decode('utf-8')
                self.assertIsNotNone(feed)
                if py_rssw_request_hander.get_content_type().find("text/html") > -1:
                    self.assertRegex(feed, ".*<channel.*")
                content = py_rssw_request_hander.get_content("http://www.google.Fr", {}) # test with dummy url, just to check there is no exception raised
                self.assertIsNotNone(content)
                self.assertRegex(content, ".*<html.*")

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    unittest.TextTestRunner().run(HandlersTest())
