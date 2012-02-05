import sys
import string
import optparse
import logging
import os
from FileReader import FileReader
from Lexer import Lexer
from Parser import tryParseWholeFileScope

def Main():
    oParser = optparse.OptionParser(usage='usage: %prog [options] minx-source-file\n')
    oParser.add_option('-l', '--loglevel', default="WARNING", help='set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    oParser.add_option('-t', '--test', action='store_true', default=False, help='run the tests')
    (options, args) = oParser.parse_args()

    numeric_log_level = getattr(logging, options.loglevel.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError('Invalid log level: %s' % options.loglevel)
    logging.basicConfig(level=numeric_log_level)

    if options.test:
        testPath = "./test-valid-programs/"
        for path in os.listdir(testPath):
            if path[-5:] == ".minx":
                logging.debug("running test: {0}".format(path))
                tokenSource = Lexer(FileReader(testPath + path))
                expression = tryParseWholeFileScope(tokenSource)
        print "tests all passed"
 	
    elif len(args) != 1:
        oParser.print_help()
    else:
        tokenSource = Lexer(FileReader(args[0]))
            
        expression = tryParseWholeFileScope(tokenSource)
        print repr(expression)

if __name__ == '__main__':
    Main()

