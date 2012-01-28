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
        self.lineBreaks = [(0, -1, "\r\n")]

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
            lastBreak = self.lineBreaks[-1]
            if lastBreak[1] == self.position - 1 and lastBreak[2] == '\r' and char == '\n':
                self.lineBreaks[-1] = (len(self.lineBreaks), self.position, '\r\n')
            else:
                self.lineBreaks.append((len(self.lineBreaks) + 1, self.position, char)) 

    def getIf(self, test):
        char = self.get()
        if char != None and test(char):
            return char
        else:
            self.unget(char)

    def getIfEqualTo(self, testStr):
        matched = []
        for c in testStr:
            char = self.getIf(lambda x : x == c)
            if char == None:
                for m in reversed(matched):
                    self.unget(m)
                return
            else:
                matched.append(char)
        return matched

    def getWhile(self, test):
        got = []
        char = self.getIf(test)
        while char != None:
            got.append(char)
            char = self.getIf(test)        
        return got
        

    def unget(self, char):
        self.position -= 1
        self.ungetted.append(char)

    def skipWhitespace(self):
        self.captureWhitespace()

        while self.skipCommentsAndNewLines():
            self.captureWhitespace()

    def skipCommentsAndNewLines(self):
        found = False
        char = self.getIfEqualTo("#")
        if char != None:
            found = True
            self.getWhile(lambda char: char != "\r" and char != "\n")

        if len(self.getWhile(lambda char: char == "\r" or char == "\n")) > 0:
            found = True

        return found
        
    def captureWhitespace(self):
        self.getWhile(lambda char: char in ''.join(map(chr, [0,9,12,32])))


    def previousLineBreak(self):
        for br in reversed(self.lineBreaks):
            if br[1] <= self.position:
                return br

    def lineAndColNo(self):
        prevLineBreak = self.previousLineBreak()
        return (prevLineBreak[0] + 1, self.position - prevLineBreak[1])


def error(msg, charSource):
    lineAndColNo = charSource.lineAndColNo()
    raise Exception("{0}: line: {1}, col: {2}".format(msg, lineAndColNo[0], lineAndColNo[1]))


TOKEN_STRING = 0
TOKEN_CASE = 1
TOKEN_NAME = 2
TOKEN_INFIX = 3
TOKEN_META = 4
TOKEN_DOLLAR = 5
TOKEN_LIST = 6
TOKEN_SCOPE = 7

TOKEN_UNION_TYPE = 8
TOKEN_MEMBER_ACCESS = 9
TOKEN_AS = 10
TOKEN_HIDE = 11

TOKEN_APPLICATION = 12

def tryParseOne(charSource, parserList):
    charSource.skipWhitespace()
    for parser in parserList:
        parsed = parser(charSource)
        if parsed != None:
            return parsed

def tryParseFromCharList(charSource, token, validList):
    captured = charSource.getWhile(lambda char: char in validList)
    return None if len(captured) == 0 else (token, ''.join(captured))


def tryParseMeta(charSource):
    char = charSource.getIfEqualTo("'")
    if char != None:
        expression = tryParseOne(charSource, [tryParseExpression])
        if expression == None:
            error("expected expression between single quotes for meta ", charSource)

        charSource.skipWhitespace()
        endChar = charSource.getIfEqualTo("'")
        if endChar == None:
            error("expected closing single quote for meta", charSource)

        return (TOKEN_META, expression)

def tryParseGroup(charSource):
    char = charSource.getIfEqualTo("(")
    if char != None:
        expression = tryParseOne(charSource, [tryParseExpression])
        if expression == None:
            error("expected expression between parentheses \"()\"", charSource)

        charSource.skipWhitespace()
        endChar = charSource.getIfEqualTo(")")
        if endChar == None:
            error("expected closing parenthesis \")\"", charSource)

        return expression

def tryParseCase(charSource):
    case = charSource.getIfEqualTo("case")
    if case != None:
        exp = tryParseOne(charSource, [tryParseNonUnionExpression])
        if exp == None:
            error("expected expression as starting point for case statement", charSource)
        logging.debug("parsed case generator expression: {0}".format(repr(exp)))

        branches = []

        charSource.skipWhitespace()
        while charSource.getIfEqualTo("|") != None:
            # TODO compare pattern with "else".
            branchPattern = tryParseOne(charSource, [tryParseExplicitScope, tryParseName, tryParseInfix])
            if branchPattern == None:
                error("expected pattern for this branch of the case statement", charSource)
                
            logging.debug("parsed: {0}".format(repr(branchPattern)))
            if branchPattern[0] in [TOKEN_NAME, TOKEN_INFIX]:
                branchPattern_type = tryParseOne(charSource, [tryParseName])
                branchPattern = [branchPattern, branchPattern_type]

            logging.debug("parsed case branch pattern: {0}".format(repr(branchPattern)))

            charSource.skipWhitespace()
            if charSource.getIfEqualTo(":") == None:
                error("expected \":\" after pattern in case branch.", charSource)

            branchExp = tryParseOne(charSource, [tryParseNonUnionExpression])
            if branchExp == None:
                error("expected expression for this branch of the case statement", charSource)
            logging.debug("parsed case branch expression: {0}".format(repr(branchExp)))

            branches.append((branchPattern, branchExp))
            charSource.skipWhitespace()
        
        if len(branches) == 0:
            error("case statements require at least one branch (expected |)", charSource)

        return (TOKEN_CASE, exp, branches)

tryParseNonUnionExpression = lambda charSource : tryParseExpression(charSource, False)

def tryParseExpression(charSource, includeUnions = True): 
    # try to parse starters first; then if match found, try to parse trailers
    mainParsers = [
      tryParseDollar, 
      tryParseGroup, 
      tryParseMeta, 
      tryParseExplicitScope, 
      tryParseList, 
      tryParseCase,
      tryParseName,
      tryParseInfix,
      tryParseString]

    expression = tryParseOne(charSource, mainParsers)

    if expression == None:
        return None      

    stillMatching = True
    while stillMatching:
        stillMatching = False

        if includeUnions:
            charSource.skipWhitespace()
            char = charSource.getIfEqualTo("|")
            if (char != None):
                nextExpression = tryParseExpression(charSource)
                if nextExpression == None:
                    error("expected expression for next type in union after \"|\"", charSource)
                if nextExpression[0] == TOKEN_UNION_TYPE:
                    expression = (TOKEN_UNION_TYPE, [expression] + nextExpression[1])
                else:
                    expression = (TOKEN_UNION_TYPE, [expression, nextExpression])
                stillMatching = True

        charSource.skipWhitespace()
        char = charSource.getIfEqualTo("@")
        if (char != None):
            member_name = tryParseOne(charSource, [tryParseName, tryParseInfix])
            if member_name == None:
                error("expected member name after member-access character \"@\"", charSource)
            expression = (TOKEN_MEMBER_ACCESS, expression, member_name)
            stillMatching = True

        charSource.skipWhitespace()
        match = charSource.getIfEqualTo("as")
        if (match == None):
            match = charSource.getIfEqualTo("hide")
        if (match != None):
            filter = tryParseExpression(charSource, includeUnions)
            if filter == None:
                error("expected filter after cast \"{0}\"".format(char), charSource)
            expression = (TOKEN_AS if char == "as" else TOKEN_HIDE, expression, filter)
            stillMatching = True

        nextExpression = tryParseOne(charSource, mainParsers)
        if (nextExpression != None):
            expression = (TOKEN_APPLICATION, expression, nextExpression)
            stillMatching = True

    return expression

def tryParseString(charSource):
    char = charSource.getIfEqualTo("\"")
    if char != None:
        strContents = []
        lastCharWasBackslash = False
        char = charSource.get()
        while lastCharWasBackslash or char != "\"":
            strContents.append(char)
            lastCharWasBackslash = (lastCharWasBackslash == False) and char == "\\"
            char = charSource.get()
        return (TOKEN_STRING, ''.join(strContents))


def compareIndents(lastIndent, newIndent):
    n1 = len(lastIndent)
    n2 = len(newIndent)
    for i in range(min(n1, n2)):
        if lastIndent[i] != newIndent[i]:
            error("whitespace is inconsistent with previous line - indentation cannot be guessed", charSource)
    return n2 - n1


# currently matches atom-values and atom-types too
tryParseName = lambda charSource: tryParseFromCharList(charSource, TOKEN_NAME, "_?.!~`$" + string.ascii_letters + string.digits)
tryParseInfix = lambda charSource: tryParseFromCharList(charSource, TOKEN_INFIX, "*+-></^%")

def tryParseDollar(charSource,):
    char = charSource.getIfEqualTo("$")
    if char != None:
        return (TOKEN_DOLLAR,)

def tryParseList(charSource):
    char = charSource.getIfEqualTo("[")
    if char != None:
        contents = []

        charSource.skipWhitespace()
        atEnd = charSource.getIfEqualTo("]") != None
        while atEnd == False:
            exp = tryParseOne(charSource, [tryParseExpression])
            if exp == None:
                error('Expected expression in list definition', charSource) 

            contents.append(exp)

            charSource.skipWhitespace()
            comma = charSource.getIfEqualTo(",")
            if comma == None:
                atEnd = charSource.getIfEqualTo("]") != None
                if atEnd == False:
                    error('Expected end bracket (\"]\") for list end or comma for item separation.', charSource)

        return (TOKEN_LIST, contents)

def tryParseExplicitScope(charSource):
    char = charSource.getIfEqualTo("{")
    if char != None:
        scopeDeclarations = []

        nameParsers = [tryParseExplicitScope, tryParseName, tryParseInfix]

        charSource.skipWhitespace()
        atEnd = charSource.getIfEqualTo("}") != None
        while atEnd == False:
            declaration = tryParseOne(charSource, nameParsers)
            if declaration == None:
                error('Expected name declaration in scope definition', charSource) 
                
            logging.debug("parsed: {0}".format(repr(declaration)))
            declaration_type = None
            if declaration[0] in [TOKEN_NAME, TOKEN_INFIX]:
                declaration_type = tryParseOne(charSource, [tryParseExpression])

            value = None
            charSource.skipWhitespace()
            equals = charSource.getIfEqualTo("=")
            if equals != None:
                value = tryParseOne(charSource, [tryParseExpression])
                if value == None:
                    error('Expected value after equals sign in scope declaration', charSource) 

            scopeDeclarations.append((declaration, declaration_type, value))

            charSource.skipWhitespace()
            comma = charSource.getIfEqualTo(",")
            if comma == None:
                atEnd = charSource.getIfEqualTo("}") != None
                if atEnd == False:
                    error('Expected end brace (\"}\")for scope end or comma for member separation.', charSource)

        return (TOKEN_SCOPE, scopeDeclarations)


def Main():

    oParser = optparse.OptionParser(usage='usage: %prog [options] minx-source-file\n')
    oParser.add_option('-l', '--loglevel', default="WARNING", help='set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    (options, args) = oParser.parse_args()

    numeric_log_level = getattr(logging, options.loglevel.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError('Invalid log level: %s' % options.loglevel)
    logging.basicConfig(level=numeric_log_level)

    if len(args) != 1:
        oParser.print_help()
    else:
        charSource = FileReader(args[0])
        expression = tryParseOne(charSource, [tryParseExplicitScope])
        print repr(expression)

if __name__ == '__main__':
    Main()

