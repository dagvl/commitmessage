#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""The controller and utils for the CVS SCM (http://www.cvshome.org)."""

import fileinput
import os
import re
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Controller

class CvsController(Controller):
    """Translates CVS loginfo/commitinfo information into the Model"""

    def __init__(self, test):
        self.test = test

    def getTest(self):
        return self.test


