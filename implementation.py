import sys
import string
import optparse
import logging
import os


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
                self.lineBreaks[-1] = (lastBreak[0], self.position, '\r\n')
            else:
                self.lineBreaks.append((lastBreak[0] + 1, self.position, char)) 

    def getIf(self, test):
        char = self.get()
        if char != None and test(char):
            return char
        else:
            self.unget(char)

    def isNextChar(self, testChar):
        return self.getIf(lambda x : x == testChar) != None

    def isAtEnd(self):
        char = self.get()
        if char == None:
            return True
        self.unget(char)

    def getWhile(self, test):
        got = []
        char = self.getIf(test)
        while char != None:
            got.append(char)
            char = self.getIf(test)        
        return ''.join(got)

    def getFromString(self, string):
        return self.getWhile(lambda char: char in string)
        
    def unget(self, char):
        self.position -= 1
        self.ungetted.append(char)

    def previousLineBreak(self):
        for br in reversed(self.lineBreaks):
            if br[1] <= self.position:
                return br

    def lineAndColNo(self):
        prevLineBreak = self.previousLineBreak()
        return (prevLineBreak[0] + 1, self.position - prevLineBreak[1])

class Tokenizer():
    def __init__(self, charSource):
        self.charSource = charSource
        self.indentStack = ['']
        self.captureIndent()
        self.ungetted = [(TOKEN_FILESTART,)]

    def get(self):
        if len(self.ungetted) != 0:
            return self.ungetted.pop()

        if self.charSource.isAtEnd():
            return (TOKEN_FILEEND,)

        for capturer in [self.captureIndent, self.captureSymbol, self.captureName, self.captureInfix, self.captureString]:
            token = capturer()
            if token != None:
                return token

        self.error("unrecognised token")

    def getIfOfType(self, tokenType):
        token = self.get()
        if token != None:
            if token[0] == tokenType:
                return token
            else:
                self.unget(token)

    def isNextToken(self, tokenType):
        return self.getIfOfType(tokenType) != None

    def unget(self, token):
        self.ungetted.append(token)

    def captureIndent(self):
        self.captureWhitespace()

        indent = None
        while self.skipCommentsAndNewLines():
            indent = self.captureWhitespace()

        if self.charSource.isAtEnd():
            # ignore the indent - just unget outstanding unindents and eof.
            self.unget((TOKEN_FILEEND,))
            self.queueFurtherUnindents('')
            return self.ungetted.pop()

        if indent != None:
            lastIndent = self.indentStack[-1]
            diff = self.compareIndents(lastIndent, indent)
            if diff > 0:
                self.indentStack.append(indent)
                return (TOKEN_INDENT,)
            elif diff == 0:
                return (TOKEN_NEWLINE,)
            else:
                # an unindent is strictly speaking one or more unindents, then 
                # a newline at the old indentation level
                self.indentStack.pop()
                self.unget((TOKEN_NEWLINE,))
                self.queueFurtherUnindents(indent)
                return (TOKEN_UNINDENT,)

    def compareIndents(self, lastIndent, newIndent):
        n1 = len(lastIndent)
        n2 = len(newIndent)
        for i in range(min(n1, n2)):
            if lastIndent[i] != newIndent[i]:
                self.error("whitespace is inconsistent with previous line - indentation cannot be guessed")
        return n2 - n1

    def queueFurtherUnindents(self, indent):
        lastIndent = self.indentStack[-1]
        diff = self.compareIndents(lastIndent, indent)
        if diff > 0:
            self.error("cannot unindent to new indentation")
        elif diff < 0:
            # multiple unindents - store on the ungetted queue
            self.indentStack.pop()
            self.queueFurtherUnindents(indent)
            self.unget((TOKEN_UNINDENT,)) 

    def skipCommentsAndNewLines(self):
        foundComment = self.charSource.isNextChar("#")
        if foundComment:
            self.charSource.getWhile(lambda char: char != "\r" and char != "\n")

        return len(self.charSource.getFromString("\r\n")) > 0 or foundComment
        
    def captureWhitespace(self):
        return self.charSource.getFromString(''.join(map(chr, [0,9,12,32])))

    def captureSymbol(self):        
        singleSymbols = {
            "{" : TOKEN_OPEN_BRACE,
            "}" : TOKEN_CLOSE_BRACE,
            "[" : TOKEN_OPEN_BRACKET,
            "]" : TOKEN_CLOSE_BRACKET,
            "(" : TOKEN_OPEN_PARENTHESES,
            ")" : TOKEN_CLOSE_PARENTHESES,
            "$" : TOKEN_DOLLAR,
            "," : TOKEN_COMMA,
            "'" : TOKEN_SINGLEQUOTE,
            "@" : TOKEN_AT
        }
        
        char = self.charSource.getIf(lambda c: c in singleSymbols)
        if char != None:
            logging.debug("found symbol: {0}".format(char))
            return (singleSymbols[char],)

    def captureName(self):
        namesMap = {
            "case" : TOKEN_CASE,
            "else" : TOKEN_ELSE,
            "as" : TOKEN_AS,
            "hide" : TOKEN_HIDE}

        return self.captureChars("_?.`" + string.ascii_letters + string.digits, namesMap, TOKEN_NAME)

    def captureInfix(self):
        infixMap = {
            "=" : TOKEN_EQUALS,
            "|" : TOKEN_PIPE,
            ":" : TOKEN_COLON}

        return self.captureChars("^*/%+-:><=&|", infixMap, TOKEN_INFIX)

    def captureChars(self, validChars, patterns, tokenType):
        match = self.charSource.getFromString(validChars)

        lowerMatch = match.lower()
        if lowerMatch in patterns:
            return (patterns[lowerMatch],)
        if len(match) > 0:
            hasSideEffects = self.charSource.isNextChar('~')
            isMutable = self.charSource.isNextChar('!')
            return (tokenType, match, hasSideEffects, isMutable)

    def captureString(self):
        if self.charSource.isNextChar("\""):
            strContents = []
            lastCharWasBackslash = False
            char = self.charSource.get()
            while lastCharWasBackslash or char != "\"":
                strContents.append(char)
                lastCharWasBackslash = (lastCharWasBackslash == False) and char == "\\"
                char = self.charSource.get()
            return (TOKEN_STRING, ''.join(strContents))

    def error(self, msg):
        lineAndColNo = self.charSource.lineAndColNo()
        raise Exception("{0}: line: {1}, col: {2}. Next token:{3}".format(msg, lineAndColNo[0], lineAndColNo[1], repr(self.get())))

TOKEN_OPEN_BRACE = 0
TOKEN_CLOSE_BRACE = 1
TOKEN_OPEN_BRACKET = 2
TOKEN_CLOSE_BRACKET = 3
TOKEN_OPEN_PARENTHESES = 4
TOKEN_CLOSE_PARENTHESES = 5
TOKEN_DOLLAR = 6
TOKEN_EQUALS = 7
TOKEN_COLON = 8
TOKEN_PIPE = 9
TOKEN_COMMA = 10
TOKEN_SINGLEQUOTE = 11
TOKEN_AT = 12

TOKEN_CASE = 13
TOKEN_ELSE = 14
TOKEN_AS = 15
TOKEN_HIDE = 16

TOKEN_STRING = 17
TOKEN_NAME = 18
TOKEN_INFIX = 19

TOKEN_INDENT = 20
TOKEN_UNINDENT = 21
TOKEN_NEWLINE = 22

TOKEN_FILESTART = 23
TOKEN_FILEEND = 24


PARSED_STRING = 0 # string contains names to match
PARSED_CASE = 1  # expression, [branchpattern1, branchpattern2, branchexp], elseExp
PARSED_NAME = 2  # string, hasSideEffects, isMutable
PARSED_INFIX = 3 # string, hasSideEffects, isMutable
PARSED_META = 4   # expression
PARSED_DOLLAR = 5
PARSED_LIST = 6  # [expression]
PARSED_SCOPE = 7  # [declaration, declarationType, valueExp]

# precedences:
PARSED_UNION_TYPE = 9 # [expression]
PARSED_AS = 10 # expression, filter
PARSED_HIDE = 11 # expression, filter
PARSED_APPLICATION = 12 # expression1, expression2
PARSED_INFIX_OPERATION = 13 # operator, lhs, rhs
PARSED_MEMBER_ACCESS = 8 # expression, membername

def tryParseOne(tokenSource, parserList):
    for parser in parserList:
        parsed = parser(tokenSource)
        if parsed != None:
            return parsed

def tryParseMeta(tokenSource):
    if tokenSource.isNextToken(TOKEN_SINGLEQUOTE):
        expression = tryParseExpression(tokenSource)
        if expression == None:
            tokenSource.error("expected expression between single quotes for meta ")

        if tokenSource.isNextToken(TOKEN_SINGLEQUOTE) == False:
            tokenSource.error("expected closing single quote for meta")

        return (PARSED_META, expression)

def tryParseGroup(tokenSource):
    if tokenSource.isNextToken(TOKEN_OPEN_PARENTHESES):
        expression = tryParseUnion(tokenSource)
        if expression == None:
            tokenSource.error("expected expression between parentheses \"()\"")

        if tokenSource.isNextToken(TOKEN_CLOSE_PARENTHESES) == False:
            tokenSource.error("expected closing parenthesis \")\"")

        return expression

def tryParseCase(tokenSource):
    if tokenSource.isNextToken(TOKEN_CASE):
        exp = tryParseExpression(tokenSource)
        if exp == None:
            tokenSource.error("expected expression as starting point for case statement")
        logging.debug("parsed case generator expression: {0}".format(repr(exp)))

        branches = []
        elseBranch = None
        pipesAreIndented = tokenSource.isNextToken(TOKEN_INDENT)

        while tokenSource.isNextToken(TOKEN_PIPE):
            if elseBranch != None:
                tokenSource.error("An else branch must be the last branch of a case statement.")
            isElse = False
            branchPattern = tryParseOne(tokenSource, [tryParseExplicitScope, tryParseName, tryParseInfix])
            branchPattern_type = None
            if branchPattern == None:
                isElse = tokenSource.isNextToken(TOKEN_ELSE)
                if isElse == False:
                    tokenSource.error("expected pattern for this branch of the case statement")

            elif branchPattern[0] in [PARSED_NAME, PARSED_INFIX]:
                branchPattern_type = tryParseName(tokenSource)

            logging.debug("parsed case branch pattern: {0}, type {1}".format(repr(branchPattern), repr(branchPattern_type)))

            if tokenSource.isNextToken(TOKEN_COLON) == False:
                tokenSource.error("expected \":\" after pattern in case branch.")

            branchExp = tryParseOne(tokenSource, [tryParseImplicitScope, tryParseExpression])
            if branchExp == None:
                tokenSource.error("expected expression for this branch of the case statement")
            logging.debug("parsed case branch expression: {0}".format(repr(branchExp)))

            if isElse:
                elseBranch = branchExp
            else:
                branches.append((branchPattern, branchPattern_type, branchExp))
            if pipesAreIndented:
                if tokenSource.isNextToken(TOKEN_UNINDENT):
                    break
                elif tokenSource.isNextToken(TOKEN_NEWLINE) == False:
                    tokenSource.error("expected indentation matching first branch in the case statement")
        
        if len(branches) == 0:
            tokenSource.error("case statements require at least one non-else branch (expected |)")

        return (PARSED_CASE, exp, branches, elseBranch)




def tryParseBaseExpression(tokenSource):
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

    return tryParseOne(tokenSource, mainParsers)

def tryParseMemberAccess(tokenSource):
    expression = tryParseBaseExpression(tokenSource)
    if expression == None:
        return None

    while tokenSource.isNextToken(TOKEN_AT):
        subexp = tryParseOne(tokenSource, [tryParseName, tryParseInfix])
        if subexp == None:
            tokenSource.error("expected member name after member-access character \"@\"")
        expression = (PARSED_MEMBER_ACCESS, expression, subexp)

    return expression

class DoublyLinkedList():
    def __init__(self, item, isSentinel = False):
        self.left = None
        self.right = None
        self.item = item
        self.isSentinel = isSentinel

    def insertToLeft(self, node):
        if node != None:
            node.left = self.left
            if self.left != None:
                self.left.right = node
            node.right = self
            self.left = node

    def remove(self):
        if self.left != None:
            self.left.right = self.right
        if self.right != None:
            self.right.left = self.left
        self.left = None
        self.right = None

opsInOrder = "^*/%+-:><=&|"

def greatestPrecedence(currentBestNode, newNode):
    if currentBestNode == None:
        return newNode
    
    currentInfix = currentBestNode.item[1]
    newInfix = newNode.item[1]

    n1 = len(currentInfix)
    n2 = len(newInfix)
    for i in range(min(n1, n2)):
        prec1 = opsInOrder.find(currentInfix[i])
        prec2 = opsInOrder.find(newInfix[i])
        if prec2 < prec1:
            return newNode
        if prec1 < prec2:
            return currentBestNode

    return newNode if n1 > n2 else currentBestNode 

# TODO this runs in n^2 at the mo, but premature optimization, right?
def tryParseApplication(tokenSource):

    leftSentinel = DoublyLinkedList(None, True)
    rightSentinel = DoublyLinkedList(None, True)
    rightSentinel.insertToLeft(leftSentinel)

    exp = tryParseMemberAccess(tokenSource)
    while exp != None:
        expNode = DoublyLinkedList(exp)
        rightSentinel.insertToLeft(expNode)
        exp = tryParseMemberAccess(tokenSource)

    # first collapse infix operators
    while True:
        nextNode = leftSentinel.right
        highestOpNode = None
        while nextNode.isSentinel == False:
            if nextNode.item[0] == PARSED_INFIX:
                highestOpNode = greatestPrecedence(highestOpNode, nextNode)
            nextNode = nextNode.right

        if highestOpNode != None:
            leftOperand = None
            rightOperand = None
            if highestOpNode.left.isSentinel == False:
                leftOperand = highestOpNode.left.item
                highestOpNode.left.remove()
            if highestOpNode.right.isSentinel == False:
                rightOperand = highestOpNode.right.item
                highestOpNode.right.remove()
            highestOpNode.item = (PARSED_INFIX_OPERATION, highestOpNode.item, leftOperand, rightOperand)
        else:
            break

    # last collapse function applications
    penultimateNode = rightSentinel.left
    if penultimateNode.isSentinel:
        return

    while penultimateNode.left.isSentinel == False:
        function = penultimateNode.left.item
        penultimateNode.left.remove()
        penultimateNode.item = (PARSED_APPLICATION, function, penultimateNode.item)

    return penultimateNode.item

def tryParseHide(tokenSource):
    expression = tryParseApplication(tokenSource)
    if expression == None:
        return None

    while tokenSource.isNextToken(TOKEN_HIDE):
        subexp = tryParseApplication(tokenSource)
        if subexp == None:
            tokenSource.error("expected cast after \"hide\"")
        expression = (PARSED_HIDE, expression, subexp)

    return expression

def tryParseExpression(tokenSource):
    expression = tryParseHide(tokenSource)
    if expression == None:
        return None

    while tokenSource.isNextToken(TOKEN_AS):
        subexp = tryParseHide(tokenSource)
        if subexp == None:
            tokenSource.error("expected cast after \"as\"")
        expression = (PARSED_AS, expression, subexp)

    return expression

def tryParseUnion(tokenSource): 
    exp = tryParseExpression(tokenSource)

    if exp == None:
        return None
    expressions = [exp]

    while tokenSource.isNextToken(TOKEN_PIPE):
        exp = tryParseExpression(tokenSource)
        if exp == None:
            tokenSource.error("expected expression for next type in union after \"|\"")
        expressions.append(exp)

    if len(expressions) > 1:
        return (PARSED_UNION_TYPE, expressions)
    return expressions[0]

def tryParseString(tokenSource):
    token = tokenSource.getIfOfType(TOKEN_STRING)
    return (PARSED_STRING, token[1]) if token != None else None

def tryParseDollar(tokenSource):
    return (PARSED_DOLLAR, ) if tokenSource.isNextToken(TOKEN_DOLLAR) else None

def tryParseTokenQuad(tokenSource, tokenType, parsedType):
    token = tokenSource.getIfOfType(tokenType)
    return (parsedType, token[1], token[2], token[3]) if token != None else None

tryParseName = lambda tokenSource: tryParseTokenQuad(tokenSource, TOKEN_NAME, PARSED_NAME)
tryParseInfix = lambda tokenSource: tryParseTokenQuad(tokenSource, TOKEN_INFIX, PARSED_INFIX)

def tryParseList(tokenSource):
    if tokenSource.isNextToken(TOKEN_OPEN_BRACKET):
        contents = []

        atEnd = tokenSource.isNextToken(TOKEN_CLOSE_BRACKET)
        while atEnd == False:
            exp = tryParseUnion(tokenSource)
            if exp == None:
                tokenSource.error('Expected expression in list definition') 

            contents.append(exp)

            if tokenSource.isNextToken(TOKEN_COMMA) == False:
                atEnd = tokenSource.isNextToken(TOKEN_CLOSE_BRACKET)
                if atEnd == False:
                    tokenSource.error('Expected end bracket (\"]\") for list end or comma for item separation.')

        return (PARSED_LIST, contents)


tryParseExplicitScope = lambda tokenSource: tryParseScope(tokenSource, TOKEN_OPEN_BRACE, TOKEN_COMMA, TOKEN_CLOSE_BRACE)
tryParseImplicitScope = lambda tokenSource: tryParseScope(tokenSource, TOKEN_INDENT, TOKEN_NEWLINE, TOKEN_UNINDENT)
tryParseWholeFileScope = lambda tokenSource: tryParseScope(tokenSource, TOKEN_FILESTART, TOKEN_NEWLINE, TOKEN_FILEEND)

def tryParseScope(tokenSource, startToken, separatorToken, endToken):
    if tokenSource.isNextToken(startToken):
        logging.debug("found scope start token: {0}".format(startToken))
        scopeDeclarations = []

        nameParsers = [tryParseExplicitScope, tryParseName, tryParseInfix]

        atEnd = tokenSource.isNextToken(endToken)
        while atEnd == False:
            declaration = tryParseOne(tokenSource, nameParsers)
            if declaration == None:
                tokenSource.error('Expected name declaration in scope definition') 
                
            logging.debug("parsed declaration: {0}".format(repr(declaration)))
            declaration_type = None
            if declaration[0] in [PARSED_NAME, PARSED_INFIX]:
                declaration_type = tryParseUnion(tokenSource)
                logging.debug("parsed declaration type: {0}".format(repr(declaration_type)))

            value = None
            if tokenSource.isNextToken(TOKEN_EQUALS):
                logging.debug("found equals sign")
                value = tryParseOne(tokenSource, [tryParseImplicitScope, tryParseUnion])
                logging.debug("parsed value: {0}".format(repr(value)))
                if value == None:
                    tokenSource.error('Expected value after equals sign in scope declaration') 

            scopeDeclarations.append((declaration, declaration_type, value))

            if tokenSource.isNextToken(separatorToken) == False:
                atEnd = tokenSource.isNextToken(endToken)
                if atEnd == False:
                    tokenSource.error('Expected scope end or comma for member separation.')

        return (PARSED_SCOPE, scopeDeclarations)


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
                tokenSource = Tokenizer(FileReader(testPath + path))
                expression = tryParseWholeFileScope(tokenSource)
        print "tests all passed"
 	
    elif len(args) != 1:
        oParser.print_help()
    else:
        tokenSource = Tokenizer(FileReader(args[0]))
            
        expression = tryParseWholeFileScope(tokenSource)
        print repr(expression)

if __name__ == '__main__':
    Main()

