import sys
import string
import optparse
import logging
import os

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

TOKEN_STRING = 16
TOKEN_NAME = 17
TOKEN_INFIX = 18

TOKEN_INDENT = 19
TOKEN_UNINDENT = 20
TOKEN_NEWLINE = 21

TOKEN_FILESTART = 22
TOKEN_FILEEND = 23

class Lexer():
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
            "as" : TOKEN_AS}

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

