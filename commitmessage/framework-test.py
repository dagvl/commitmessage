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

    def testRootDirectoryIdentity(self):
        """Make sure getting the root directory works."""
        self.assertEquals(1, self.model.rootDirectory() is self.model.directory('/'))

    def testOne(self):
        """Simple test of adding a dir to the model."""
        self.model.addDirectory(Directory('/test1/'))
        self.assertEquals(1, len(self.model.rootDirectory().subdirectories()))
        # Test gcd
        self.assertEquals('/test1/', self.model.greatestCommonDirectory())
        # Test # of dirs
        self.assertEquals(2, len(self.model.directories()))

    def testTwo(self):
        """Add two directories, one after the other."""
        a = Directory('/a/', 'added')
        b = Directory('/a/b/', 'added')

        self.model.addDirectory(a)
        self.model.addDirectory(b)
        self.assertEquals(1, a is self.model.directory('/a/'))
        self.assertEquals(1, b is self.model.directory('/a/b/'))

        root = self.model.rootDirectory()
        self.assertEquals(1, len(root.subdirectories()))
        self.assertEquals(1, len(root.subdirectories()[0].subdirectories()))
        self.assertEquals('added', root.subdirectories()[0].action())
        self.assertEquals('/a/b/', root.subdirectories()[0].subdirectories()[0].path())
        self.assertEquals('added', root.subdirectories()[0].subdirectories()[0].action())
        # Test gcd
        self.assertEquals('/a/', self.model.greatestCommonDirectory())

    def testGcdWithAction(self):
        dir1 = Directory('/a/a/a/', 'added')
        dir2 = Directory('/a/a/b/', 'removed')
        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)
        self.model.directory('/a/').action('modified')
        self.assertEquals('/a/', self.model.greatestCommonDirectory())

    def testGcdWithFiles(self):
        dir1 = Directory('/a/a/a/', 'added')
        dir2 = Directory('/a/a/b/', 'removed')
        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)
        File('x.txt', self.model.directory('/a/'), 'added')
        self.assertEquals('/a/', self.model.greatestCommonDirectory())

    def testTwoDifferentDownThree(self):
        """Added two separate directories, a few levels down."""
        dir1 = Directory('/a/a/a/', 'removed')
        dir2 = Directory('/a/a/b/', 'removed')
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
        # Test gcd
        self.assertEquals('/a/a/', self.model.greatestCommonDirectory())
        # Test files()
        self.assertEquals(2, len(self.model.files('added')))
        self.assertEquals('x.txt', self.model.files('added')[0].name())
        # Test file
        self.assertEquals('x.txt', self.model.file('/a/a/a/x.txt').name())

    def testFilesFilter(self):
        dir = Directory('/module1/')
        f = File('x.txt', dir, 'added')
        f = File('y.txt', dir, 'modified')
        self.assertEquals(1, len(dir.files('added')))
        self.assertEquals(1, len(dir.files('modified')))

    def testDirectory(self):
        dir = self.model.directory('/x/y/')
        self.assertEquals(3, len(self.model.directories()))

    def testModelWithRootFileChange(self):
        f = File('x.txt', self.model.rootDirectory(), 'added')
        self.assertEquals(1, len(self.model.files()))
        self.assertEquals(1, len(self.model.directoriesWithFiles('added')))
        self.assertEquals(1, len(self.model.directories()))
        self.assertEquals(self.model.rootDirectory(), self.model.directory('/'))
        self.assertEquals('/', self.model.greatestCommonDirectory())

if __name__ == '__main__':
    unittest.main()
