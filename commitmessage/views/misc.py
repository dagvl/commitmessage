#!/usr/bin/env python
#
# commitmessage 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Provides several email Views for the commitmessage framework."""

import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.framework import View

class DumpView(View):
    """Provides unit testing capabilities by doing a simple dump of the Model to
    a text file."""

    def execute(self):
        f = file(self.file(), 'w')

        addedFiles = self.model.files('added')
        addedDirs = self.model.directories('added')
        if len(addedFiles) > 0 or addedDirs > 0:
            f.write('Added:\n')
            for file in addedFiles:
                f.write('  %s\n' % file.path())
            for dir in addedDirs:
                f.write('  %s\n' % dir.path())
        f.close()

    def file(self, file=None):
        """The path of the file to dump the Model to."""
        if file is not None: self.__file = file
        return self.__file
