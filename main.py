#!/usr/bin/env python3
from http.server import HTTPServer
from server import Server
import logging
import os
import ssl
import sys
import getopt
import ntpath
from config.Config import Config


def main(argv):
    config: Config = Config(parseCommandLine(argv))

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    httpd = HTTPServer((config.getServerListeningHostName(),
                        config.getServerListeningPort()), Server)
    httpd.server_name = config.getServerServingHostName()
    http_prefix = "http"
    if not config.getKeyFile() is None and not config.getCertFile() is None:
        http_prefix = "https"
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       keyfile=config.getKeyFile(),
                                       certfile=config.getCertFile(), server_side=True)

    logging.getLogger().info('Server Starts - %s://%s:%d serving %s://%s:%d urls' % (
        http_prefix,
        config.getServerListeningHostName(),
        config.getServerListeningPort(),
        http_prefix,
        config.getServerServingHostName(),
        config.getServerListeningPort()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.getLogger().info('Server Stops')


def parseCommandLine(argv: list) -> str:
    config_file = None

    try:
        opts, args = getopt.getopt(argv[1:], "hc:", ["config="])
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
