#!/usr/bin/python

#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""A MVC framework for capturing information from scm systems.

"""

import string

class File:
    """Represents a file that has been affected by the commit."""

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/commitmessage.py."""
        if path != None: self._path = path
        return self._path

    def action(self, action=None):
        """the action that was performed: added, removed, modified, moved, branch"""
        if action != none: self._action = action
        return self._action

    def rev(self, rev=None):
        """The new revision number for the file."""
        if rev != None: self._rev = rev
        return self._rev

    def delta(self, delta=None):
        """The number of lines that changed, e.g. +1/-5"""
        if delta != None: self._delta = delta
        return self._data

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
        
        >>> f = File()
        >>> f.path('/dir/file.txt')
        '/dir/file.txt'
        >>> f.directory()
        '/dir'
        """
        if self._directory == None:
        #if '_directory' not in self.__dict__.keys():
            dirs = string.split(self.path(), '/')
            self._directory = string.join(dirs[0:-1], '/')
        return self._directory

class Directory:
    """Represents a directory that has been affected by the commit."""

    def path(self, path=None):
        """The path relative to the repository root, e.g. CVSROOT/testdir."""
        if path != None: self._path = path
        return self._path

    def action(self, action=None):
        """the action that was performed: added, removed, modified, moved, branch"""
        if action != none: self._action = action
        return self._action

    def movedToPath(self, movedToPath=None):
        """If the action=moved, then the new path. Otherwise None."""
        if movedToPath != None: self.movedToPath = movedToPath
        return self._movedToPath

class Model:
    """Wraps the model that gets sent between the Controller and Views."""

    def __init__(self, user):
        self.user = user
        self.files = []
        self.directories = []
        self.indirectlyAffectedDirectories = []

    def addDirectory(self, directory, action, movedTo=None):
        self.directories.append(Directory(directory, action, movedTo))

    def addFile(self, action, rev, delta, rcsfile, diff, movedTo=None):
        self.files.append(File(action, rev, delta, rcsfile, diff, movedTo))

def _test():
    """Executes doctest on this module."""
    import doctest, commitmessage
    return doctest.testmod(commitmessage)

if __name__ == "__main__":
    _test()
