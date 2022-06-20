#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Tests the basic functionality of the util module."""

import unittest
import os
import sys

if __name__ == '__main__':
    sys.path.append('../')

from commitmessage.framework import Model
from commitmessage.main import CmException
from commitmessage.util import CmConfigParser, getNewInstance

class TestNewInstance(unittest.TestCase):
    """Tests the getNewInstance method."""

    def testCvsController(self):
        c = getNewInstance('commitmessage.controllers.cvs.CvsController')
        self.assertEqual('CvsController', c.__class__.__name__)
        c.__init__(None, None, None)

    def testBadController(self):
        self.assertRaises(CmException, getNewInstance, 'blah.blah.BlahController')

class BaseConfigTest(unittest.TestCase):
    """Implements setUp for tests that test the configuration parsing."""

    def setUp(self):
        self.config = CmConfigParser('commitmessage/commitmessage.conf')

    def testModules(self):
        """Makes sure the modules are being read in correctly."""
        expected = {
            'cvsroot': '^/CVSROOT',
            'ibm2': '^/ibm2',
            'stephen': '^/stephen',
            'stephen-misc': '^/stephen/misc',
            'module1': '^/'}
        for name, value in list(expected.items()):
            self.assertEqual(value, self.config.get('modules', name))
        self.assertEqual(len(expected), len(self.config.options('modules')))

    def testViews(self):
        """Makes sure the views are being read in correctly."""
        expected = {
            'bombsight': 'commitmessage.views.bugtracking.FogBugzView',
            'email': 'commitmessage.views.email.TigrisStyleEmailView',
            'dump': 'commitmessage.views.misc.DumpView'}
        for name, value in list(expected.items()):
            self.assertEqual(value, self.config.get('views', name))
        self.assertEqual(len(expected), len(self.config.options('views')))

    def testGetModulesForPath(self):
        """Test getting the modules for a given path."""
        self.assertEqual(['cvsroot', 'module1'], self.config.getModulesForPath('/CVSROOT/blah/bar.txt'))
        self.assertEqual(['module1', 'stephen'], self.config.getModulesForPath('/stephen/etc/etc/bar.txt'))
        self.assertEqual(['module1', 'stephen', 'stephen-misc'], self.config.getModulesForPath('/stephen/misc/bar.txt'))

    def testGetViewsForModule(self):
        """Test getting the views for a given module."""
        expected = {
            'cvsroot': ['email', 'bombsight'],
            'stephen': ['email', 'bombsight'],
            'ibm2': ['bombsight'],
            'module1': ['dump', 'email']}
        model = Model()
        for key, value in list(expected.items()):
            views = self.config.getViewsForModule(key, model)
            for view in views:
                self.assertEqual(1, expected[key].index(view.name) > -1)
                if view.name == 'email':
                    self.assertEqual('@beachead.com', view.keyword_from())
            self.assertEqual(len(expected[key]), len(views))

if __name__ == '__main__':
    unittest.main()
