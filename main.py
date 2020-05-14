#!/usr/bin/env python3
from server.pyrssw_server import PyRSSWHTTPServer
import logging
import os
import sys
from utils.arguments import parse_command_line
from config.config import Config


def main(argv):

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    Config.instance().load_config_file(parse_command_line(argv))
    httpd = PyRSSWHTTPServer()

    logging.getLogger().info('Server Starts - %s serving %s urls' % (
        httpd.get_listening_url_prefix(),
        httpd.get_serving_url_prefix()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.getLogger().info('Server Stops')



if __name__ == '__main__':
    main(sys.argv)