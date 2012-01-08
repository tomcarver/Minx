import sys
import string
import optparse
import logging


class FileReader:
    def __init__(self, file):
        self.file = file
        self.infile = open(file, 'rb')
        self.ungetted = []
        self.position = -1
        self.lineBreaks = []

    def get(self):
        if len(self.ungetted) != 0:
            self.position += 1
            return self.ungetted.pop()
        char = self.infile.read(1)
        if not char:
            self.infile.close()
            return None
        self.position += 1
        self.recordLineBreak(char)
        return char

    def recordLineBreak(self, char):
        if (char == '\r' or char == '\n'):
            lastBreak = self.lineBreaks[-1] if len(self.lineBreaks) > 0 else None
            if lastBreak != None and lastBreak[0] == self.position - 1 and lastBreak[2] == '\r' and char == '\n':
                self.lineBreaks[-1] = (self.position, len(self.lineBreaks), '\r\n')
            else:
                self.lineBreaks.append((self.position, len(self.lineBreaks) + 1, char)) 

    def get_n(self, n):
        return [get() for _ in range(n)]

    def unget(self, char):
        self.position -= 1
        self.ungetted.append(char)

    def unget_n(self, chars):
        self.position -= len(chars)
        self.ungetted.extend(reversed(chars))

    def previousLineBreak(self):
        for br in reversed(self.lineBreaks):
            if br[0] <= self.position:
                return br

    def lineAndColNo(self):
        prevLineBreak = self.previousLineBreak()
        if prevLineBreak == None:
            prevLineBreak = (-1, 0) 
        return (prevLineBreak[1] + 1, self.position - prevLineBreak[0])


def error(msg, charSource):
    lineAndColNo = charSource.lineAndColNo()
    raise Exception("{0}: line: {1}, col: {2}".format(msg, lineAndColNo[0], lineAndColNo[1]))


TOKEN_STRING = 0
TOKEN_COMMENT = 1

TOKEN_NAME = 2
TOKEN_INFIX = 3
TOKEN_META = 4
TOKEN_GROUP = 5
TOKEN_LIST = 6
TOKEN_EXPLICIT_SCOPE = 7

TOKEN_NEW_LINE = 8
TOKEN_INDENT = 9
TOKEN_UNINDENT = 10
TOKEN_WHITESPACE = 11 # ignore

TOKEN_PIPE = 12
TOKEN_AT = 13
TOKEN_EQUALS = 14
TOKEN_COLON = 15

def parseAllWhile(charSource, whileCondition, parserList):
    tokens = []
    next = parseOneFromList(charSource, parserList)
    while whileCondition(next):
        logging.debug("parsed: {0}".format(repr(next)))
        tokens.append(next)
        next = parseOneFromList(charSource, parserList)
    return tokens

def parseOneFromList(charSource, parserList):
    if charSource:
        for parser in parserList:
            parsed = parser(charSource, parserList)
            if parsed != None:
                print repr(parsed)
                return parsed

        char = charSource.get()
        if char:
            error('Could not parse. next char:"{0}". parserList:{1}'.format(char, repr(parserList)), charSource)

captureWhitespace = lambda charSource: captureCharsFromList(charSource, ''.join(map(chr, [0,9,12,32])))
captureNewLine = lambda charSource: captureCharsFromList(charSource, "\r\n")

def captureCharsFromList(charSource, validList):
    captured = []
    char = charSource.get()
    while char != None and char in validList:
        captured.append(char)
        char = charSource.get()
    charSource.unget(char)
    return ''.join(captured)

def tryParseFromList(charSource, parserList, token, validList):
    match = captureCharsFromList(charSource, validList)
    return None if len(match) == 0 else (token, match)

def tryParseSingleChar(charSource, parserList, token, charToMatch):
    char = charSource.get()
    if char != None and char == charToMatch:
        return (token,)
    charSource.unget(char)

def tryParseRegion(charSource, parserList, token, startChar, endChar):
    char = charSource.get()
    if char != None and char == startChar:
        # capture all in parserList until endChar found
        tryParseRegionEnd = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, None, endChar)

        contents = parseAllWhile(
            charSource,
            lambda nextToken: nextToken[0] != None, 
            [tryParseRegionEnd] + parserList)

        return (token, contents)
    charSource.unget(char)

tryParseComma = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, ",", ",")

def tryParseCommaSeparatedRegion(charSource, parserList, token, startChar, endChar):
    char = charSource.get()
    if char != None and char == startChar:
        # capture all in contentParsers until endChar found
        tryParseRegionEnd = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, None, endChar)
        parseAnotherSetContainer = [True]

        def parseWhile(nextToken):
            parseAnotherSetContainer[0] = nextToken[0] != None
            return nextToken[0] != None and nextToken[0] != ","

        contents = []

        while parseAnotherSetContainer[0]:
            contents.append(parseAllWhile(
                charSource,
                parseWhile, 
                [tryParseRegionEnd, tryParseComma] + parserList))

        return (token, contents)
    charSource.unget(char)

def tryParseString(charSource, parserList):
    char = charSource.get()
    if char != None and char == "\"":
        strContents = []
        lastCharWasBackslash = False
        char = charSource.get()
        while lastCharWasBackslash or char != "\"":
            strContents.append(char)
            lastCharWasBackslash = (lastCharWasBackslash == False) and char == "\\"
            char = charSource.get()
        return (TOKEN_STRING, ''.join(strContents))
    charSource.unget(char)

def tryParseComment(charSource, parserList):
    char = charSource.get()
    if char != None and char == "#":
        commentContents = []
        char = charSource.get()
        while char != None and char != "\r" and char != "\n":
            commentContents.append(char)
            char = charSource.get()
            
        return (TOKEN_COMMENT, ''.join(commentContents))
    charSource.unget(char)

def tryParseWhitespace(charSource, parserList, lastIndent, forceIndent = False):
    # just whitespace, no new-lines => omit
    ws = captureWhitespace(charSource)
    br = captureNewLine(charSource)
    while len(br) > 0:
        ws = captureWhitespace(charSource)
        br = captureNewLine(charSource)

    # if there were new-lines, classify as indent, unindent or new-line
    if len(br) > 0 or forceIndent:
        n1 = len(lastIndent)
        n2 = len(ws)
        for i in range(min(n1, n2)):
            if lastIndent[i] != ws[i]:
                error("whitespace is inconsistent with previous line - indentation cannot be guessed", charSource)
        if n2 > n1:
            return (TOKEN_INDENT, ws)
        elif n1 < n2:
            return (TOKEN_UNINDENT, ws)
        else:
            return (TOKEN_NEW_LINE, ws)

TODO capture whitespace token if not indent or unindent or newline

tryParseName = lambda charSource, parserList: tryParseFromList(charSource, parserList, TOKEN_NAME, "_?.!~`$" + string.ascii_letters + string.digits)
tryParseInfix = lambda charSource, parserList: tryParseFromList(charSource, parserList, TOKEN_INFIX, "*+-></^%")

tryParsePipe = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, TOKEN_PIPE, "|")
tryParseAt = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, TOKEN_AT,"@")
tryParseEquals = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, TOKEN_EQUALS, "=")
tryParseColon = lambda charSource, parserList: tryParseSingleChar(charSource, parserList, TOKEN_COLON, ":")

tryParseMeta = lambda charSource, parserList: tryParseRegion(charSource, parserList, TOKEN_META, "'", "'")
tryParseGroup = lambda charSource, parserList: tryParseRegion(charSource, parserList, TOKEN_GROUP, "(", ")")

tryParseList = lambda charSource, parserList: tryParseCommaSeparatedRegion(charSource, parserList, TOKEN_LIST, "[", "]")
tryParseExplicitScope = lambda charSource, parserList: tryParseCommaSeparatedRegion(charSource, parserList, TOKEN_EXPLICIT_SCOPE, "{", "}") 

def parse(charSource):
    indentContainer = [tryParseWhitespace(charSource, [], "", True)[1]]

    def tryParseIndent(charSource, parserList):
        token = tryParseWhitespace(charSource, parserList, indentContainer[0])
        if (token != None):
            indentContainer[0] = token[1]
        return token

    # must parse indent first - strips out any whitespace we want ignored.
    parsers = [
        tryParseIndent,
        tryParseString,
        tryParseComment,
        tryParseName,
        tryParseInfix,
        tryParsePipe,
        tryParseAt,
        tryParseEquals,
        tryParseColon,
        tryParseMeta,
        tryParseGroup,
        tryParseList,
        tryParseExplicitScope]

    return parseAllWhile(
        charSource,
        lambda nextToken: nextToken != None, 
        parsers)

def Main():

    oParser = optparse.OptionParser(usage='usage: %prog [options] minx-source-file\n')
    (options, args) = oParser.parse_args()

    if len(args) != 1:
        oParser.print_help()
    else:
        charSource = FileReader(args[0])
        expression = parse(charSource)
        print repr(expression)

if __name__ == '__main__':
    Main()
