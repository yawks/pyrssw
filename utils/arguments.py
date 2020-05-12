import getopt
import ntpath
import sys

def parse_command_line(argv: list) -> str:
    config_file = ""

    try:
        opts, _ = getopt.getopt(argv[1:], "hc:", ["config="])
    
        for opt, arg in opts:
            if opt == '-h':
                print_help(argv[0], 0)
            elif opt in ("-c", "--config"):
                config_file = arg

    except getopt.GetoptError:
        print_help(argv[0], 2)

    return config_file

def print_help(script_name, exit_code):
    print(ntpath.basename(script_name) + ' -c <optional config file>')
    sys.exit(exit_code)