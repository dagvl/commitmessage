#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Tests the basic functionality of the framework module, specifically the
Model/Directory interaction."""

import unittest
import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Model, Directory, File

class TestDirectoryHierarchy(unittest.TestCase):
    """Tests added levels of directories."""

    def setUp(self):
        """Creates an empty model to work against."""
        self.model = Model()

    def testOne(self):
        """Simple test of adding a dir to the model."""
        self.model.addDirectory(Directory('/test1'))
        self.assertEquals(1, len(self.model.rootDirectory().subdirectories()))

        self.assertEquals('/test1', self.model.greatestCommonDirectory())

    def testTwo(self):
        """Add two directories, one after the other."""
        self.model.addDirectory(Directory('/a', 'added'))
        self.model.addDirectory(Directory('/a/b', 'added'))

        root = self.model.rootDirectory()
        self.assertEquals(1, len(root.subdirectories()))
        self.assertEquals(1, len(root.subdirectories()[0].subdirectories()))
        self.assertEquals('added', root.subdirectories()[0].action())
        self.assertEquals('/a/b', root.subdirectories()[0].subdirectories()[0].path())
        self.assertEquals('added', root.subdirectories()[0].subdirectories()[0].action())

        self.assertEquals('/a', self.model.greatestCommonDirectory())

    def testTwoDifferentDownThree(self):
        """Added two separate directories, a few levels down."""
        dir1 = Directory('/a/a/a', 'removed')
        dir2 = Directory('/a/a/b', 'removed')
        File('x.txt', dir1, 'added')
        File('y.txt', dir2, 'added')

        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)

        root = self.model.rootDirectory()
        self.assertEquals(1, len(root.subdirectories()))
        a1 = root.subdirectories()[0]
        self.assertEquals(1, len(a1.subdirectories()))
        a2 = a1.subdirectories()[0]
        self.assertEquals(2, len(a2.subdirectories()))
        a3 = a2.subdirectories()[0]
        b3 = a2.subdirectories()[1]

        self.assertEquals('removed', a3.action())
        self.assertEquals('removed', b3.action())

        self.assertEquals('/a/a', self.model.greatestCommonDirectory())

        self.assertEquals(2, len(self.model.files('added')))
        self.assertEquals('x.txt', self.model.files('added')[0].name())

    def testFilesFilter(self):
        dir = Directory('/module1')
        f = File('x.txt', dir, 'added')
        f = File('y.txt', dir, 'modified')
        self.assertEquals(1, len(dir.files('added')))
        self.assertEquals(1, len(dir.files('modified')))

if __name__ == '__main__':
    unittest.main()
