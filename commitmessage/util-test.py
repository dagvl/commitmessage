#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Tests the basic functionality of the unil module."""

import unittest
import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Model
from commitmessage.main import CmException
from commitmessage.util import CmConfigParser, getNewInstance

class TestNewInstance(unittest.TestCase):
    """Tests the getNewInstance method."""

    def testCvsController(self):
        c = getNewInstance('commitmessage.controllers.cvs.CvsController')
        self.assertEquals('CvsController', c.__class__.__name__)

        c.__init__('foo')
        self.assertEquals('foo', c.getTest())

    def testBadController(self):
        self.assertRaises(CmException, getNewInstance, 'blah.blah.BlahController')

class BaseConfigTest(unittest.TestCase):
    """Implements setUp for tests that test the configuration parsing."""

    def setUp(self):
        self.config = CmConfigParser('commitmessage/commitmessage.conf')

    def testModules(self):
        """Makes sure the modules are being read in correctly."""
        expected = {
            'cvsroot': '^CVSROOT',
            'ibm2': '^ibm2',
            'stephen': '^stephen',
            'stephen-misc': '^stephen/misc'}
        for name, value in expected.items():
            self.assertEquals(value, self.config.get('modules', name))
        self.assertEquals(len(expected), len(self.config.options('modules')))

    def testViews(self):
        """Makes sure the views are being read in correctly."""
        expected = {
            'bombsight': 'commitmessage.views.bugtracking.FogBugzView',
            'email': 'commitmessage.views.email.HtmlEmailView'}
        for name, value in expected.items():
            self.assertEquals(value, self.config.get('views', name))
        self.assertEquals(len(expected), len(self.config.options('views')))

    def testGetModulesForPath(self):
        """Test getting the modules for a given path."""
        self.assertEquals(['cvsroot'], self.config.getModulesForPath('CVSROOT/blah/bar.txt'))
        self.assertEquals(['stephen'], self.config.getModulesForPath('stephen/etc/etc/bar.txt'))
        self.assertEquals(['stephen', 'stephen-misc'], self.config.getModulesForPath('stephen/misc/bar.txt'))

    def testGetViewsForModule(self):
        """Test getting the views for a given module."""
        expected = {
            'cvsroot': ['email', 'bombsight'],
            'stephen': ['email', 'bombsight'],
            'ibm2': ['bombsight']}
        model = Model()
        model.baseDirectory('blah')
        for key, value in expected.items():
            views = self.config.getViewsForModule(key, model)
            for view in views:
                self.assertEquals(1, expected[key].index(view.name) > -1)
                if view.name == 'email':
                    self.assertEquals('stephen@beachead.com', view.keyword_from())
            self.assertEquals(len(expected[key]), len(views))

if __name__ == '__main__':
    unittest.main()
