#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""
Provides the model classes for the commitmessage framework.
"""

import os
import string
import sys

from commitmessage.exceptions import CmException
from commitmessage.attribute import attribute

class Controller:
    """
    A base implementation for SCM-specific controllers to extend; mostly
    does the generic Views handling.
    """

    # A temp directory to dump the diff files to.
    TMPDIR = os.environ.get('TMP', None) or os.environ.get('TEMP', None) or '/tmp'

    def __init__(self, config, argv, stdin):
        """
        Initializes the controller's model and saves the references to argv and stdin.

        @param config: a L{commitmessage.util.CmConfigParser} created by L{commitmessage.main}
        @param argv: the command line arguments, as gathered by L{commitmessage.main}
        @param stdin: where to stream responses to
        """
        self.config = config
        self.argv = argv
        self.stdin = stdin
        self.model = Model()

    def process(self):
        """Starts the SCM-agnostic process of building the model and executing the views."""
        self._populateModel()

        # Allow cvs to halt the process as it's data is cached between per-directory executions
        if self._stopProcessForNow():
            return

        self._executeViews()

    def _populateModel(self):
        """
        This should be overridden by concrete controllers with their
        implementation-specific logic for populating the model.
        """
        raise CmException('The controller did not override the _populateModel method.')

    def _stopProcessForNow(self):
        """
        Gives CVS a chance to kill the current process and wait for the next
        one as it has to build up data between discrete per-directory executions.
        """
        return False

    def _executeViews(self):
        """Executes the views for each module that matches the commit's base directory."""
        modules = self.config.getModulesForPath(self.model.greatestCommonDirectory())
        for module in modules:
            views = self.config.getViewsForModule(module, self.model)
            for view in views:
                view.execute()

class File:
    """Represents a file that has been affected by the commit."""

    def __init__(self, name, directory, action):
        """
        @param name: the file name, e.g. C{foo.txt}
        @param directory: the parent directory, the file will automatically add itself to this directory
        @param action: the action performed on this file that required a commit, SCM-dependent
        """
        if name.find('/') != -1:
            raise CmException, "File names may not have foward slashes in them."

        self._name = name
        self._directory = directory
        self._action = action
        self._rev = None
        self._delta = None
        self._diff = None

        self.directory.addFile(self)

    name = attribute('_name', permit='r', doc="""The file name (C{foo.txt})""")
    directory = attribute('_directory', permit='r', doc="""The L{Directory} the file is in""")
    action = attribute('_action', permit='r', doc="""The action on thie file that required a commit, SCM-dependent""")
    rev = attribute('_rev', doc="""The revision number (SCM-dependent, could be per-file or per-commit) for this file""")
    delta = attribute('_delta', doc="""The number of lines added/removed/changed in this commit""")
    diff = attribute('_diff', doc="""The diff of what changed in the file""")

    def __str__(self):
        """@return: the path of the file"""
        return '<File %s>' % self.path

    def path():
        doc = """The full path (C{/dir/foo.txt}) of the file"""
        def fget(self):
            return self.directory.path + self.name
        return locals()
    path = property(**path())

class Directory:
    """Represents a directory that has been affected by the commit."""

    def __init__(self, path, action='none'):
        if path == '' or not path.startswith('/') or not path.endswith('/'):
            raise CmException, 'Directory paths must start with a forward slash and end with a forward slash.'

        self._path = path
        self._action = action
        self._files = []
        self._subdirectories = []

    path = attribute('_path', permit='r', doc="""The full path of the directory (C{/dir/dir/})""")
    action = attribute('_action', permit='r', doc="""The action performed on this directory that caused the commit""")
    files = attribute('_files', permit='r', doc="""The L{File}s within this directory affected by the commit""")
    subdirectories = attribute('_subdirectories', permit='r', doc="""The L{Directory}s within this directory affected by the commit""")

    def name():
        doc = """The name of the directory (C{dir} with no slashes)"""
        def fget(self):
            if self.path == '/':
                return '/'
            else:
                # The path will be /aaa/bbb/name/
                return self.path.split('/')[-2]
        return locals()
    name = property(**name())

    def __str__(self):
        """@return: the path of the directory"""
        return """<Directory '%s'>""" % self.path

    def filesByAction(self, action):
        """@return: all of the files in this directory affected by the commit"""
        if action == None:
            return self.files
        else:
            return filter(lambda file: file.action == action, self.files)

    def file(self, name):
        """@return: the file in the current directory with C{name} or C{None}"""
        for file in self.files:
            if file.name == name:
                return file
        return None

    def subdirectory(self, name):
        """@return: the subdirectory with C{name} or C{None}"""
        for dir in self.subdirectories:
            if dir.name == name:
                return dir
        return None

    def hasSubdirectory(self, name):
        """@return: whether the directory has a subdirectory with C{name}."""
        for dir in self.subdirectories:
            if dir.name == name:
                return True
        return False

    def addFile(self, file):
        """Saves a file object into this directory."""
        self.files.append(file)

    def addSubdirectory(self, subdir):
        """Saves a directory object into this directory."""
        self.subdirectories.append(subdir)

class Model:
    """
    Wraps the L{File}s and L{Directory}s that get sent between the Controller and Views.
    """

    def __init__(self):
        self._rootDirectory = Directory('/')
        self._user = ''

    rootDirectory = attribute('_rootDirectory', permit='r', doc="""The root directory within the SCM""")
    user = attribute('_user', doc="""The user performing the commit""")
    log = attribute('_log', doc="""The comment the user entered for this commit""")

    def directory(self, path):
        """
        @return: the model's L{Directory} for C{path}; creates new directories and sub directories if needed
        """
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
        """
        Adds C{directory} into the model's directory tree.

        Uses C{self.directory(path)}, except it takes a default value for the
        new directory to add at the bottom of the hierarchy.
        """
        # Leave off last name and last slash to get the parent directory
        parentPath = '/'.join(directory.path.split('/')[0:-2]) + '/'
        parentDirectory = self.directory(parentPath)
        if not parentDirectory.hasSubdirectory(directory.name):
            parentDirectory.addSubdirectory(directory)

    def greatestCommonDirectory(self):
        """@return: the greatest common directory of the commit to base the module matching on"""
        dir = self.rootDirectory
        while dir.action == 'none' \
            and len(dir.subdirectories) == 1 \
            and len(dir.files) == 0:
            dir = dir.subdirectories[0]
        return dir.path

    def file(self, path):
        """@return: the L{File} for the C{path}"""
        if path == '':
            raise CmException, "File paths may not be empty."
        if path[0] != '/' or path[-1] == '/':
            raise CmException, "File paths must begin with a forward slash and not end with a back slash."
        parts = path.split('/')

        # Leave off the file name to get the parent directory
        parentDirectoryPath = '/'.join(parts[0:-1]) + '/'

        return self.directory(parentDirectoryPath).file(parts[-1])

    def files(self, action=None):
        """@return: a flat list of L{File}s, optionally those that match C{action}"""
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
        """@return: a flat list of L{Directory}s, optionally those that match C{action}."""
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
        """@return: a flat list of L{Directory}s that have changes to files"""
        return self._directoriesWithFiles(self.rootDirectory, action)

    def _directoriesWithFiles(self, directory, action):
        """
        Internal helper method to recursively build a flat list of directories
        that contain changes to files in them.
        """
        dirs = []
        if len(directory.filesByAction(action)) > 0:
            dirs.append(directory)
        for subdir in directory.subdirectories:
            dirs.extend(self._directoriesWithFiles(subdir, action))
        return dirs

class View:
    """Provides a base View for specific implementations to extend."""

    def __init__(self, name, model):
        """Initializes a new view given it's instance C{name} and C{model}."""
        self.acceptance = 0
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

