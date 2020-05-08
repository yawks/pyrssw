#!/usr/bin/env python3
from server.pyrssw_server import PyRSSWHTTPServer
import logging
import os
import sys
import getopt
import ntpath
from config.config import Config


def main(argv):
    config: Config = Config(parse_command_line(argv))

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    httpd = PyRSSWHTTPServer(config)

    logging.getLogger().info('Server Starts - %s serving %s urls' % (
        httpd.get_listening_url_prefix(),
        httpd.get_serving_url_prefix()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.getLogger().info('Server Stops')


def parse_command_line(argv: list) -> str:
    config_file = ""

    try:
        opts, _ = getopt.getopt(argv[1:], "hc:", ["config="])
    except getopt.GetoptError:
        print_help(argv[0], 2)

    for opt, arg in opts:
        if opt == '-h':
            print_help(argv[0], 0)
        elif opt in ("-c", "--config"):
            config_file = arg

    return config_file


def print_help(script_name, exit_code):
    print(ntpath.basename(script_name) + ' -c <optional config file>')
    sys.exit(exit_code)


if __name__ == '__main__':
    main(sys.argv)