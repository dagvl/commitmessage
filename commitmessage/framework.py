#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Provides the core classes for the commitmessage framework."""

import os
import string
import sys

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
        self._populateModel()

        # Allow cvs to halt the process as it's data is cached between per-directory executions
        if self._stopProcessForNow():
            return

        self._executeViews()

    def _populateModel(self):
        """This should be over-ridden by concrete controllers with their implementation-specific logic."""
        raise CmException('The controller did not override the _populateModel method.')

    def _stopProcessForNow(self):
        """Gives CVS a chance to kill the current process and wait for the next
        one as it has to build up data between discrete per-directory executions."""
        return 0

    def _executeViews(self):
        """Fires off the views for each module that matches the commits base directory."""
        modules = self.config.getModulesForPath(self.model.greatestCommonDirectory())
        for module in modules:
            views = self.config.getViewsForModule(module, self.model)
            for view in views:
                view.execute()

class DomainObject:
    """Puts in some getter/setter infrastructure."""

    def __init__(self, readonly={}):
        # Use __dict__ to avoid going to __setattr__
        self.__dict__['readonly'] = readonly
        for key, value in self.readonly.items():
            self.__dict__[key] = value

    def _upper(self, name):
        return name[0].upper() + name[1:]

    def __setattr__(self, name, value):
        """Optionally delegate checking out to setters."""

        if self.readonly.has_key(name):
            raise CmException, 'The attribute %s is read only.' % name

        setter = 'set%s' % self._upper(name)
        if hasattr(self, setter):
            method = getattr(self, setter)
            if callable(method):
                method(value)
                return

        # There was no setter, go ahead and accept the attribute
        self.__dict__[name] = value

    def __getattr__(self, name):
        """Does some simple calculated values."""
        getter = 'get%s' % self._upper(name)
        if hasattr(self, getter):
            method = getattr(self, getter)
            if callable(method):
                return method()

        # There was no getter to calculate the value, so fall back with it not being a valid attribute
        raise AttributeError, 'Attribute %s does not have a valid getter or simply does not exist.' % name

class File(DomainObject):
    """Represents a file that has been affected by the commit."""

    def __init__(self, name, directory, action):
        """Files must be owned by a parent directory; by virtue of being created, this file is added to its parent directory."""
        if name.find('/') != -1:
            raise CmException, "File names may not have foward slashes in them."

        # Set up the read only attributes
        DomainObject.__init__(self, {'name': name, 'directory': directory})

        self.action = action
        self.rev = None
        self.delta = None
        self.diff = None

        self.directory.addFile(self)

    def __str__(self):
        """Returns the path of the file."""
        return '<File %s>' % self.path

    def setName(self, value):
        raise CmException, 'The file''s name cannot be changed.'

    def setDirectory(self, value):
        raise CmException, 'The file''s directory cannot be changed.'

    def getPath(self):
        return self.directory.path + self.name

class Directory(DomainObject):
    """Represents a directory that has been affected by the commit."""

    def __init__(self, path, action='none'):
        if path == '' or not path.startswith('/') or not path.endswith('/'):
            raise CmException, 'Directory paths must start with a forward slash and end with a forward slash.'

        # Setup the read only attribute
        DomainObject.__init__(self, {'path': path, 'files': [], 'subdirectories': []})

        self.action = action

    def __repr__(self):
        """Return the path of the directory."""
        return """<Directory '%s'>""" % self.path

    def __str__(self):
        return self.__repr__()

    def setPath(self, value):
        raise CmException, 'A directory''s path cannot be changed.'

    def getName(self):
        """Returns just the name of the directory, e.g. testdir with no slashes."""
        if self.path == '/':
            return '/'
        else:
            # The path will be /aaa/bbb/name/
            return self.path.split('/')[-2]

    def filesByAction(self, action):
        """Returns all of the files in this directory affected by the commit."""
        if action == None:
            return self.files
        else:
            return filter(lambda file: file.action == action, self.files)

    def file(self, name):
        """Return a file in the current directory with the given name, or else None if it doesn't exist."""
        for file in self.files:
            if file.name == name:
                return file
        return None

    def subdirectory(self, name):
        """Return a subdirectory with a specific name."""
        for dir in self.subdirectories:
            if dir.name == name:
                return dir
        return None

    def hasSubdirectory(self, name):
        """Returns whether the directory has a subdirectory named 'name'."""
        for dir in self.subdirectories:
            if dir.name == name:
                return 1
        return 0

    def addFile(self, file):
        """Saves a file object into this directory."""
        self.files.append(file)

    def addSubdirectory(self, subdir):
        """Saves a directory object into this directory."""
        self.subdirectories.append(subdir)

class Model(DomainObject):
    """Wraps the model that gets sent between the Controller and Views.

    Properties are available via accessors to allow easy documentation."""

    def __init__(self):
        DomainObject.__init__(self, {'rootDirectory': Directory('/')})
        self.user = ''

    def directory(self, path):
        """Returns the Model's corresponding directory for the given path.
        Creates the new directories and its sub hierarchy if needed."""
        if path[0] != '/' or path[-1] != '/':
            raise CmException, 'Directory paths must start with a forward slash and end with a forward slash.'
        if path == '/':
            return self.rootDirectory

        parts = path.split('/')
        currentDirectory = self.rootDirectory
        for dir in parts:
            # Ignore blank parts, e.g. ['', 'a', 'a-a', '']
            if dir != '':
                if currentDirectory.hasSubdirectory(dir):
                    currentDirectory = currentDirectory.subdirectory(dir)
                else:
                    newdir = Directory(currentDirectory.path + dir + '/')
                    currentDirectory.addSubdirectory(newdir)
                    currentDirectory = newdir
        return currentDirectory

    def addDirectory(self, directory):
        """Adds a directory into the Model's directory tree along. Uses
        self.directory(path), except takes a default value for the new directory
        to add at the bottom of the hierarchy."""
        # Leave off last name and last slash to get the parent directory
        parentPath = '/'.join(directory.path.split('/')[0:-2]) + '/'
        parentDirectory = self.directory(parentPath)
        if not parentDirectory.hasSubdirectory(directory.name):
            parentDirectory.addSubdirectory(directory)

    def greatestCommonDirectory(self):
        """The greatest commont directory of a commit to base the module matching on."""
        dir = self.rootDirectory
        while dir.action == 'none' \
            and len(dir.subdirectories) == 1 \
            and len(dir.files) == 0:
            dir = dir.subdirectories[0]
        return dir.path

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
        return self._files(self.rootDirectory, action)

    def _files(self, directory, action):
        """Internal helper method to recursively build a flat list of files."""
        files = []
        for file in directory.files:
            if action is not None:
                if file.action == action:
                    files.append(file)
            else:
                files.append(file)
        for subdir in directory.subdirectories:
            files.extend(self._files(subdir, action))
        return files

    def directories(self, action=None):
        """Returns a flat list of directories with the optional filter applied to their action."""
        return self._directories(self.rootDirectory, action)

    def _directories(self, directory, action):
        """Internal helper method to recursively build a flat list of directories."""
        dirs = []
        if action is not None:
            if directory.action == action:
                dirs.append(directory)
        else:
            dirs.append(directory)
        for subdir in directory.subdirectories:
            dirs.extend(self._directories(subdir, action))
        return dirs

    def directoriesWithFiles(self, action=None):
        """Returns a flat list of directories that have changes to files in them."""
        return self._directoriesWithFiles(self.rootDirectory, action)

    def _directoriesWithFiles(self, directory, action):
        """Internal helper method to recursively build a flat list of
        directories that contain changes to files in them."""
        dirs = []
        if len(directory.filesByAction(action)) > 0:
            dirs.append(directory)
        for subdir in directory.subdirectories:
            dirs.extend(self._directoriesWithFiles(subdir, action))
        return dirs

class View:
    """Provides a base View for specific implementations to extend."""

    def __init__(self, name, model):
        """Initializes a new module given it's name."""
        self.name = name
        self.model = model

    def execute(self):
        """Provides child Views with a method they should override to provide their specific behavior."""
        pass

    def isTesting(self):
        return self.acceptance == '1'

    def dumpToTestFile(self, text):
        """Writes out text to a file called 'SubClassName.txt'."""
        f = file('%s.txt' % str(self).split(' ')[0].split('.')[-1], 'w')
        f.write(text)
        f.close()

def _test():
    """Executes doctest on this module."""
    import doctest, framework
    return doctest.testmod(framework)

if __name__ == '__main__':
    _test()
