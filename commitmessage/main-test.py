#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Containts unit tests which do a full system test."""

import fileinput
import os
import sys
import unittest

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    print(rootCmPath)
    sys.path.append(rootCmPath)

from commitmessage.util import CmConfigParser
from commitmessage.controllers.cvs import CvsController

def convertToStream(text):
    """Helper function to save text to a file and return a stream of it."""
    f = file('~/temp.cm.txt', 'w')
    f.write(text)
    f.close()
    return file('~/temp.cm.txt', 'r')

class TestCvsController(unittest.TestCase):
    """Puts the CvsController through a few tests."""

    def setUp(self):
        """Set the CVSROOT environment variable."""
        os.environ['CVSROOT'] = os.path.expanduser('~/test/cvs')
        self.olddir = os.getcwd()
        os.chdir(os.path.expanduser('~/test/module1'))

    def testFile(self):
        tests = self.parseTestFile()
        for test in tests:
            print('==== Running %s ====' % test['name'])
            conf = CmConfigParser('%s/commitmessage/commitmessage.conf' % self.olddir)

            if len(test['commitInfoArgv']) > 0:
                controller = CvsController(
                    conf,
                    test['commitInfoArgv'],
                    None)
                controller.process()

            f = file('%s/test/logInfoText.txt' % self.olddir, 'w')
            f.write(test['logInfoText'])
            f.close()
            f = file('%s/test/logInfoText.txt' % self.olddir, 'r')

            controller = CvsController(
                conf,
                test['logInfoArgv'],
                f)
            controller.process()

            f.close()

    def parseTestFile(self):
        """Parses and runs the test/cvs.txt file."""
        f = file('%s/test/cvs.txt' % self.olddir, 'r')
        lines = f.readlines()
        f.close()

        name = ''
        commitInfoArgv = []
        logInfoArgv = []
        logInfoText = ''
        dumpText = ''

        tests = []

        stage = 0
        for line in lines:
            line = line.rstrip()
            if stage == 0:
                # Print the name of the test
                if line != '----////----':
                    name = line
                else:
                    stage = stage + 1
            elif stage == 1:
                # Gather commitinfo's argv
                if line != '----////----':
                    commitInfoArgv.append(line)
                else:
                    stage = stage + 1
            elif stage == 2:
                # Gather loginfo's argv
                if line != '----////----':
                    logInfoArgv.append(line)
                else:
                    stage = stage + 1
            elif stage == 3:
                # Gather loginfo's text
                if line != '----////----':
                    logInfoText = logInfoText + line + '\n'
                else:
                    stage = stage + 1
            elif stage == 4:
                # Gather the dump result
                if line != '====////====':
                    dumpText = dumpText + line + '\n'
                else:
                    stage = stage + 1

            if stage == 5:
                tests.append({
                    'name': name,
                    'commitInfoArgv': commitInfoArgv,
                    'logInfoArgv': logInfoArgv,
                    'logInfoText': logInfoText,
                    'dumpText': dumpText})
                name = ''
                commitInfoArgv = []
                logInfoArgv = []
                logInfoText = ''
                dumpText = ''

                stage = 0
        return tests

if __name__ == '__main__':
    unittest.main()
