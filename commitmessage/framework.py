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
        return 0

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

    def __str__(self):
        """Returns the path of the file."""
        return '<File %s>' % self.path()

    def name(self, name=None):
        """The file name, e.g. blah.txt."""
        if name is not None:
            if name.find('/') != -1:
                raise CmException, "File names may not have foward slashes in them."
            self.__name = name
        return self.__name

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/commitmessage.py."""
        return self.directory().path() + self.name()

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

    def __repr__(self):
        """Return the path of the directory."""
        return """<Directory '%s'>""" % self.path()

    def __str__(self):
        return self.__repr__()

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/testdir."""
        if path is not None:
            if path == '' or not path.startswith('/') or not path.endswith('/'):
                raise CmException, 'Directory paths must start with a forward slash and end with a forward slash.'
            self.__path = path
        return self.__path

    def name(self):
        """Returns just the name of the directory, e.g. testdir."""
        if self.path() == '/':
            return '/'
        else:
            return self.path().split('/')[-2]

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

    def file(self, name):
        """Return a file in the current directory with the given name, or else
        None if it doesn't exist."""
        for f in self.files():
            if f.name() == name:
                return f
        return None

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
        self.user('')
        self.__rootDirectory = Directory('/')

    def directory(self, path):
        """Returns the Model's corresponding directory for the given path.
        Creates the new directories and its sub hierarchy if need be."""
        if path[0] != '/' or path[-1] != '/':
            raise CmException, 'Directory paths must start with a forward slash and end with a forward slash.'
        if path == '/':
            return self.rootDirectory()

        parts = path.split('/')
        currentDirectory = self.rootDirectory()
        for dir in parts:
            # Ignore blank parts, e.g. ['', 'a', 'a-a', '']
            if dir != '':
                if currentDirectory.hasSubdirectory(dir):
                    currentDirectory = currentDirectory.subdirectory(dir)
                else:
                    newdir = Directory(currentDirectory.path() + dir + '/')
                    currentDirectory.addSubdirectory(newdir)
                    currentDirectory = newdir
        return currentDirectory

    def addDirectory(self, directory):
        """Adds a directory into the Model's directory tree along. Uses
        self.directory(path), except takes a default value for the new directory
        to add at the bottom of the hierarchy."""
        # Leave off last name and last slash to get the parent directory
        parentPath = '/'.join(directory.path().split('/')[0:-2]) + '/'
        parentDirectory = self.directory(parentPath)
        if not parentDirectory.hasSubdirectory(directory.name()):
            parentDirectory.addSubdirectory(directory)

    def greatestCommonDirectory(self):
        """The greatest commont directory of a commit to base the module matching on."""
        dir = self.rootDirectory()
        while dir.action() == 'none' \
            and len(dir.subdirectories()) == 1 \
            and len(dir.files()) == 0:
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

    def file(self, path):
        """Returns the file for the given path."""
        if path == '':
            raise CmException, "File paths may not be empty."
        if path[0] != '/' or path[-1] == '/':
            raise CmException, "File paths must begin with a forward slash and not end with a back slash."
        parts = path.split('/')
        # Leave off the file name to get the parent directory
        parentDirectoryPath = '/'.join(parts[0:-1]) + '/'
        return self.directory(parentDirectoryPath).file(parts[-1])

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
        if action is not None:
            if directory.action() == action:
                dirs.append(directory)
        else:
            dirs.append(directory)
        for subdir in directory.subdirectories():
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
        if len(directory.files(action)) > 0:
            dirs.append(directory)
        for subdir in directory.subdirectories():
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
