#!/usr/bin/python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""Some minor tests of the CVS utility functions"""

import os
import sys
import unittest

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.controllers.cvs import cvs_status, cvs_diff

class TestStatus(unittest.TestCase):
    """Test the L{cvs_status} utility function"""

    def testBasic(self):
        os.chdir(os.path.expanduser('~/test/module1'))
        rev, delta = cvs_status('x.txt')
        self.assertEquals('1.6', rev)
        self.assertEquals('+2 -0', delta)

class TestDiff(unittest.TestCase):
    """Tests the L{cvs_diff} utility function"""

    def testBasic(self):
        os.chdir(os.path.expanduser('~/test/module1'))
        diff = cvs_diff('x.txt', '1.6')
        self.assertEquals(318, diff.find('+More...down...here'))

if __name__ == '__main__':
    unittest.main()

