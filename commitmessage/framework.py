#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Provides the core classes for the commitmessage framework."""

import os
import pickle
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
        self.argv = argv
        self.stdin = stdin
        self.model = Model()

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
                print('Firing view %s' % view.name)
                view.execute()

class File:
    """Represents a file that has been affected by the commit."""

    def __init__(self, name, directory, action):
        """Files must be owned by a parent directory."""
        self.__name = name
        self.__directory = directory
        self.__action = action
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

    def __init__(self, path, action='none'):
        self.path(path)
        self.action(action)
        self.__files = []
        self.__subdirectories = []

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/testdir."""
        if path is not None:
            if path != '' and not path.startswith('/'):
                raise CmException, 'Directory paths must start with a forward slash.'
            self.__path = path
        return self.__path

    def name(self):
        """Returns just the name of the directory, e.g. testdir."""
        return os.path.split(self.path())[-1]

    def action(self, action=None):
        """The action that was performed: added, removed, modified, moved, branch"""
        if action is not None: self.__action = action
        return self.__action

    def files(self):
        """Returns all of the files in this directory affected by the commit."""
        return self.__files

    def subdirectory(self, name):
        """Return a subdirectory with a specific name."""
        for dir in self.subdirectories():
            if dir.name() == name:
                return dir
        return None

    def subdirectories(self):
        """Returns all of the subdirectories in this directory with files affected by the commit."""
        return self.__subdirectories

    def hasSubdirectory(self, name):
        """Returns whether the directory has a subdirectory named 'name'."""
        for dir in self.subdirectories():
            if dir.name() == name:
                return 1
        return 0

    def addFile(self, file):
        """Saves a file object into this directory."""
        self.__files.append(file)

    def addSubdirectory(self, subdir):
        """Saves a directory object into this directory."""
        self.__subdirectories.append(subdir)

class Model:
    """Wraps the model that gets sent between the Controller and Views.

    Properties are available via accessors to allow easy documentation."""

    def __init__(self):
        self.__rootDirectory = Directory('')
        self.user(os.getenv('USER') or os.getlogin())

    def addDirectory(self, directory):
        """Adds a directory into the Model's directory tree along."""
        # Skip the first blank dir, dirs = ['', 'a', 'a-a']
        dirs = directory.path().split('/')[1:]

        currentDirectory = self.rootDirectory()
        # Skip the last one, as we don't auto-create it, it's a given param
        for dir in dirs[:-1]:
            if currentDirectory.hasSubdirectory(dir):
                currentDirectory = currentDirectory.subdirectory(dir)
            else:
                newdir = Directory('%s/%s' % (currentDirectory.path(), dir))
                currentDirectory.addSubdirectory(newdir)
                currentDirectory = newdir
        if not currentDirectory.hasSubdirectory(directory.name()):
            currentDirectory.addSubdirectory(directory)

    def greatestCommonDirectory(self):
        """The greatest commont directory of a commit to base the module matching on."""
        dir = self.rootDirectory()
        while dir.action() == 'none' and len(dir.subdirectories()) == 1:
            dir = dir.subdirectories()[0]
        return dir.path()

    def rootDirectory(self):
        """The root directory for the commit, always '' for framework simplicity."""
        return self.__rootDirectory

    def user(self, user=None):
        """The user who made the commit."""
        if user is not None: self._user = user
        return self._user

class View:
    """Provides a base View for specific implementations to extend."""

    def __init__(self, name, model):
        """Initializes a new module given it's name."""
        self.name = name
        self.model = model

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
