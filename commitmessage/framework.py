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
        """Initializes the controller's Model and saves the references to argv and stdin."""
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

    def __init__(self, directory, action):
        """Files must be owned by a parent directory."""
        self.__directory = directory;
        self.__action = action;
        directory.addFile(self)

    def name(self, name=None):
        """The file name, e.g. blah.txt."""
        if name is not None: self.__name = name
        return self.__name

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/commitmessage.py."""
        return self.directory().path() + '/' + self.name()

    def action(self, action=None):
        """The action that was performed: added, removed, modified, moved, branch."""
        if action is not None: self.__action = action
        return self.__action

    def rev(self, rev=None):
        """The new revision number for the file."""
        if rev is not None: self.__rev = rev
        return self.__rev

    def delta(self, delta=None):
        """The number of lines that changed, e.g. +1/-5"""
        if delta is not None: self.__delta = delta
        return self.__delta

    def diff(self, diff=None):
        """The unified diff of the changes."""
        if diff is not None: self.__diff = diff
        return self.__diff

    def directory(self):
        """Returns the parent directory object."""
        return self.__directory

class Directory:
    """Represents a directory that has been affected by the commit."""

    def __init__(self, path):
        self.path(path)
        self.__files = []
        self.__subdirectories = []

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/testdir."""
        if path is not None: self.__path = path
        return self.__path

    def name(self):
        """Returns just the name of the directory, e.g. testdir."""
        return self.path().split('/')[-1]

    def action(self, action=None):
        """The action that was performed: added, removed, modified, moved, branch"""
        if action is not None: self.__action = action
        return self.__action

    def files(self):
        """Returns all of the files in this directory affected by the commit."""
        return self.__files

    def subdirectories(self):
        """Returns all of hte subdirectories in this directory with files affected by the commit."""
        return self.__subdirectories

    def addFile(file):
        """Saves a file object into this directory."""
        self.__files.append(file)

    def addSubdirectory(subdir):
        """Saves a subdirectory object into this directory."""
        this.__subdirectories.append(subdir)

class Model:
    """Wraps the model that gets sent between the Controller and Views.

    Properties are available via accessors to allow easy documentation."""

    def __init__(self):
        self.user(os.getenv('USER') or os.getlogin())
        self.directories = []
        self.indirectlyAffectedDirectories = []

    def addDirectory(self, directory, action):
        """Adds a directory to the Model with its action."""
        self.directories.append(Directory(directory, action))

    def baseDirectory(self, baseDirectory=None):
        """The lowest commont directory of a commit to base the module matching on."""
        if baseDirectory is not None: self._baseDirectory = baseDirectory
        return self._baseDirectory

    def rootDirectory(self, rootDirectory=None):
        """The common root directory for the commit."""
        if rootDirectory is not None: self._rootDirectory = rootDirectory
        return self._rootDirectory

    def user(self, user=None):
        """The user who made the commit."""
        if user is not None: self._user = user
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

if __name__ == '__main__':
    _test()
