#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Containts unit tests which do a full system test."""

import unittest
import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    print(rootCmPath)
    sys.path.append(rootCmPath)

from commitmessage.util import CmConfigParser
from commitmessage.controllers.cvs import CvsController

class TestCvsController(unittest.TestCase):
    """Puts the CvsController through a few tests."""

    def testCvs(self):
        """Run the test."""
        conf = CmConfigParser('commitmessage/commitmessage.conf')
        controller = CvsController(conf)

if __name__ == '__main__':
    unittest.main()
