#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Provides the core classes for the commitmessage framework."""

import os
import string
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    sys.path.append(rootCmPath)

class Controller:
    """A base implementation for SCM-specific controllers to extend; mostly
    does the generic Views handling."""

    TMPDIR = os.environ.get('TMP', None) or os.environ.get('TEMP', None) or '/tmp'
    """A temp directory to dump the diff files to."""

    def __init__(self, config, argv, stdin):
        """ Initializes the controller's Model and saves the references to argv and stdin."""
        self.config = config
        self.model = Model()
        self.argv = argv
        self.stdin = stdin

    def process(self):
        """Starts the generalized commitmessage process of building the model and executing the views."""
        self.populateModel()

        # Allow cvs to halt the process as it's data is cached between per-directory executions
        if self.stopProcessForNow():
            return

        self.executeViews()

    def populateModel(self):
        """This should be over-ridden by concrete controllers with their implementation-specific logic."""
        pass

    def stopProcessForNow(self):
        """Gives CVS a chance to kill the current process and wait for the next
        one as it has to build up data between discrete per-directory executions."""
        return false

    def executeViews(self):
        """Fires off the views for each module that matches the commits base directory."""
        modules = self.config.getModulesForPath(this.model.baseDirectory())
        for module in modules:
            views = self.config.getViewsForModule(module, self.model)
            for view in views:
                view.execute()

class File:
    """Represents a file that has been affected by the commit."""

    def __init__(self, file, action, rev, delta, diff):
        """Files must be initialized correctly with all the given fields."""
        self.file(file)
        self.action(action)
        self.rev(rev)
        self.delta(delta)
        self.diff(diff)

    def file(self, file=None):
        """The file anem, e.g. blah.txt."""
        if file != None: self._file = file
        return self._file

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/commitmessage.py."""
        if path != None: self._path = path
        return self._path

    def action(self, action=None):
        """the action that was performed: added, removed, modified, moved, branch"""
        if action != None: self._action = action
        return self._action

    def rev(self, rev=None):
        """The new revision number for the file."""
        if rev != None: self._rev = rev
        return self._rev

    def delta(self, delta=None):
        """The number of lines that changed, e.g. +1/-5"""
        if delta != None: self._delta = delta
        return self._delta

    def diff(self, diff=None):
        """The unified diff of the changes."""
        if diff != None: self._diff = diff
        return self._diff

    def movedToPath(self, movedToPath=None):
        """If the action=moved, then the new path. Otherwise None."""
        if movedToPath != None: self.movedToPath = movedToPath
        return self._movedToPath

    def directory(self):
        """Return the path without the file name, e.g. CVSROOT.

        >>> f = File('/dir/file.txt', 'added', 1.1, '+', '<<>>')
        >>> f.path('/dir/file.txt')
        '/dir/file.txt'
        >>> f.directory()
        '/dir'
        """
        return os.path.dirname(self.path())

class Directory:
    """Represents a directory that has been affected by the commit."""

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/testdir."""
        if path != None: self._path = path
        return self._path

    def action(self, action=None):
        """The action that was performed: added, removed, modified, moved, branch"""
        if action != none: self._action = action
        return self._action

    def movedToPath(self, movedToPath=None):
        """If the action=moved, then the new path. Otherwise None."""
        if movedToPath != None: self.movedToPath = movedToPath
        return self._movedToPath

class Model:
    """Wraps the model that gets sent between the Controller and Views.

    Properties are available via accessors to allow easy documentation."""

    def __init__(self):
        self.user(os.getenv('USER') or os.getlogin())
        self.files = []
        self.directories = []
        self.indirectlyAffectedDirectories = []

    def addDirectory(self, directory, action):
        """Adds a directory to the Model with its action."""
        self.directories.append(Directory(directory, action))

    def addFile(self, file, action, rev, delta, diff):
        """Adds a file to the Model with its action, rev, delta, and diff."""
        self.files.append(File(file, action, rev, delta, diff))

    def baseDirectory(self, baseDirectory=None):
        """The lowest commont directory of a commit to base the module matching on."""
        if baseDirectory != None: self._baseDirectory = baseDirectory
        return self._baseDirectory

    def user(self, user=None):
        """The user who made the commit."""
        if user != None: self._user = user
        return self._user

class View:
    """Provides a base View for specific implementations to extend."""

    def __init__(self, name):
        """Initializes a new module given it's name."""
        self.name = name

    def execute(self):
        """Provides child Views with a method they should override to provide
        their specific behavior."""
        pass

def _test():
    """Executes doctest on this module."""
    import doctest, framework
    return doctest.testmod(framework)

if __name__ == "__main__":
    _test()
