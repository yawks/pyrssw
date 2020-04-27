#!/usr/bin/env python3
import time
from http.server import HTTPServer
from server import Server
import socket
import logging
import os
import ssl
import sys
import getopt
import ntpath

DEFAULT_HOST_NAME = socket.gethostbyaddr(socket.gethostname())[0]
DEFAULT_PORT_NUMBER = 8001


def main(argv):
    hostname, port, keyfile, certfile = getHostNameFromCommandLineArgs(argv)
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    httpd = HTTPServer((DEFAULT_HOST_NAME, port), Server)
    httpd.server_name = hostname
    ssl_log_suffix = ""
    if not keyfile is None and not certfile is None:
        ssl_log_suffix = "over https "
        httpd.socket = ssl.wrap_socket (httpd.socket,
            keyfile=keyfile,
            certfile=certfile, server_side=True)

    print(time.asctime(), 'Server Starts %s- %s:%s' % (ssl_log_suffix, hostname, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % (DEFAULT_HOST_NAME, port))

def getHostNameFromCommandLineArgs(argv):
    hostname = DEFAULT_HOST_NAME
    port = DEFAULT_PORT_NUMBER
    keyfile = None
    certfile = None

    try:
        opts, args = getopt.getopt(argv[1:], "hn:p:k:c:", ["hostname=", "port=", "keyfile=", "certfile="])
    except getopt.GetoptError:
        print_help(argv[0], 2)

    for opt, arg in opts:
        if opt == '-h':
            print_help(argv[0], 0)
        elif opt in ("-n", "--hostname"):
            hostname = arg
        elif opt in ("-p", "--port"):
            if arg.isnumeric():
                port = int(arg)
            else:
                print_help(argv[0], 2)
        elif opt in ("-k", "--keyfile"):
            keyfile = arg
        elif opt in ("-c", "--certfile"):
            certfile = arg

    return hostname, port, keyfile, certfile

def print_help(script_name, exit_code):
    print(ntpath.basename(script_name) + ' -n <hostname> -p <port> -k <key file> -c <cert file>')
    sys.exit(exit_code)


if __name__ == '__main__':
    main(sys.argv)