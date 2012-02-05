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
