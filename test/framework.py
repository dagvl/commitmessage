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
    sys.path.append('../')

from commitmessage.framework import Model, Directory, File
from commitmessage.exceptions import CmException

class TestDirectoryHierarchy(unittest.TestCase):
    """Tests added levels of directories."""

    def setUp(self):
        """Creates an empty model to work against."""
        self.model = Model()

    def testRootDirectoryIdentity(self):
        """Make sure getting the root directory works."""
        self.assertEqual(1, self.model.rootDirectory is self.model.directory('/'))

    def testOne(self):
        """Simple test of adding a dir to the model."""
        self.model.addDirectory(Directory('/test1/'))
        self.assertEqual(1, len(self.model.rootDirectory.subdirectories))
        # Test gcd
        self.assertEqual('/test1/', self.model.greatestCommonDirectory())
        # Test # of dirs
        self.assertEqual(2, len(self.model.directories()))

    def testReadOnly(self):
        d = Directory('/a/', 'added')

        try:
            d.path = 'foo'
            self.fail('path was allowed to be changed.')
        except CmException:
            pass

        try:
            d.files = []
            self.fail('files was allowed to be changed.')
        except CmException:
            pass

        try:
            d.subdirectories = []
            self.fail('subdirectories was allowed to be changed.')
        except CmException:
            pass

        f = File('y.txt', d, 'added')
        try:
            f.name = 'foo.txt'
            self.fail('name was allowed to be changed.')
        except CmException:
            pass

        try:
            f.directory = 'foo'
            self.fail('directory was allowed to be changed.')
        except CmException:
            pass

    def testValidity(self):
        try:
            d = Directory('foo')
            self.fail('directory was invalid.')
        except CmException:
            pass

        try:
            d = Directory('/foo')
            self.fail('directory was invalid.')
        except CmException:
            pass

        try:
            d = Directory('foo/')
            self.fail('directory was invalid.')
        except CmException:
            pass

        try:
            d = Directory('/')
            f = File('/foo', d, 'added')
            self.fail('file name was invalid.')
        except CmException:
            pass

    def testTwo(self):
        """Add two directories, one after the other."""
        a = Directory('/a/', 'added')
        b = Directory('/a/b/', 'added')

        self.model.addDirectory(a)
        self.model.addDirectory(b)
        self.assertEqual(1, a is self.model.directory('/a/'))
        self.assertEqual(1, b is self.model.directory('/a/b/'))

        root = self.model.rootDirectory
        self.assertEqual(1, len(root.subdirectories))
        self.assertEqual(1, len(root.subdirectories[0].subdirectories))
        self.assertEqual('added', root.subdirectories[0].action)
        self.assertEqual('/a/b/', root.subdirectories[0].subdirectories[0].path)
        self.assertEqual('added', root.subdirectories[0].subdirectories[0].action)
        # Test gcd
        self.assertEqual('/a/', self.model.greatestCommonDirectory())

    def testGcdWithAction(self):
        dir1 = Directory('/a/a/a/', 'added')
        dir2 = Directory('/a/a/b/', 'removed')
        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)
        self.model.directory('/a/').action = 'modified'
        self.assertEqual('/a/', self.model.greatestCommonDirectory())

    def testGcdWithFiles(self):
        dir1 = Directory('/a/a/a/', 'added')
        dir2 = Directory('/a/a/b/', 'removed')
        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)
        File('x.txt', self.model.directory('/a/'), 'added')
        self.assertEqual('/a/', self.model.greatestCommonDirectory())

    def testTwoDifferentDownThree(self):
        """Added two separate directories, a few levels down."""
        dir1 = Directory('/a/a/a/', 'removed')
        dir2 = Directory('/a/a/b/', 'removed')
        File('x.txt', dir1, 'added')
        File('y.txt', dir2, 'added')

        self.model.addDirectory(dir1)
        self.model.addDirectory(dir2)

        root = self.model.rootDirectory
        self.assertEqual(1, len(root.subdirectories))
        a1 = root.subdirectories[0]
        self.assertEqual(1, len(a1.subdirectories))
        a2 = a1.subdirectories[0]
        self.assertEqual(2, len(a2.subdirectories))
        a3 = a2.subdirectories[0]
        b3 = a2.subdirectories[1]

        self.assertEqual('removed', a3.action)
        self.assertEqual('removed', b3.action)
        # Test gcd
        self.assertEqual('/a/a/', self.model.greatestCommonDirectory())
        # Test files
        self.assertEqual(2, len(self.model.files('added')))
        self.assertEqual('x.txt', self.model.files('added')[0].name)
        # Test file
        self.assertEqual('x.txt', self.model.file('/a/a/a/x.txt').name)

    def testFilesFilter(self):
        dir = Directory('/module1/')
        f = File('x.txt', dir, 'added')
        f = File('y.txt', dir, 'modified')
        self.assertEqual(1, len(dir.filesByAction('added')))
        self.assertEqual(1, len(dir.filesByAction('modified')))

    def testDirectory(self):
        dir = self.model.directory('/x/y/')
        self.assertEqual(3, len(self.model.directories()))

    def testModelWithRootFileChange(self):
        f = File('x.txt', self.model.rootDirectory, 'added')
        self.assertEqual(1, len(self.model.files()))
        self.assertEqual(1, len(self.model.directoriesWithFiles('added')))
        self.assertEqual(1, len(self.model.directories()))
        self.assertEqual(self.model.rootDirectory, self.model.directory('/'))
        self.assertEqual('/', self.model.greatestCommonDirectory())

if __name__ == '__main__':
    unittest.main()
