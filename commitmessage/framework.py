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

from commitmessage.exceptions import CmException

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
        modules = self.config.getModulesForPath(self.model.greatestCommonDirectory())
        for module in modules:
            views = self.config.getViewsForModule(module, self.model)
            for view in views:
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

    def files(self, action=None):
        """Returns all of the files in this directory affected by the commit."""
        if action is None:
            return self.__files
        else:
            return filter(lambda file: file.action() == action, self.__files)

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
        if user is not None: self.__user = user
        return self.__user

    def log(self, log=None):
        """The log message the user provided when making the commit."""
        if log is not None: self.__log = log
        return self.__log

    def files(self, action=None):
        """Returns a flat list of files with the optional filter applied to
        their action."""
        return self._files(self.rootDirectory(), action)

    def _files(self, directory, action):
        """Internal helper method to recursively build a flat list of files."""
        files = []
        for file in directory.files():
            if action is not None:
                if file.action() == action:
                    files.append(file)
            else:
                files.append(file)
        for subdir in directory.subdirectories():
            files.extend(self._files(subdir, action))
        return files

    def directories(self, action=None):
        """Returns a flat list of directories with the optional filter applied
        to their action."""
        return self._directories(self.rootDirectory(), action)

    def _directories(self, directory, action):
        """Internal helper method to recursively build a flat list of directories."""
        dirs = []
        for subdir in directory.subdirectories():
            if action is not None:
                if subdir.action() == action:
                    dirs.append(subdir)
            else:
                dirs.add(subdir)
            dirs.extend(self._directories(subdir, action))
        return dirs

    def directoriesWithFiles(self, action=None):
        """Returns a flat list of directories that have changes to files in
        them."""
        return self._directoriesWithFiles(self.rootDirectory(), action)

    def _directoriesWithFiles(self, directory, action):
        """Internal helper method to recursively build a flat list of
        directories that contain changes to files in them."""
        dirs = []
        for subdir in directory.subdirectories():
            if len(subdir.files(action)) > 0:
                dirs.append(subdir)
            dirs.extend(self._directoriesWithFiles(subdir, action))
        return dirs

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
