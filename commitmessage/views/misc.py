#!/usr/bin/env python
#
# commitmessage 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Provides several email Views for the commitmessage framework."""

import os
import sys

from commitmessage.model import View

class DumpView(View):
    """Provides unit testing capabilities by doing a simple dump of the Model to
    a text file."""

    def execute(self):
        # file(...) conflicts with self.file(), so use open(.,.)
        f = open(self.file(), 'w')

        addedFiles = self.model.files('added')
        addedDirs = self.model.directories('added')
        if len(addedFiles) > 0 or len(addedDirs) > 0:
            f.write('Added:\n')
            for file in addedFiles:
                f.write('  %s\n' % file.path())
            for dir in addedDirs:
                f.write('  %s\n' % dir.path())
        modFiles = self.model.files()
        if len(modFiles) > 0:
            f.write('Modified:\n')
            for file in modFiles:
                f.write('  %s\n' % file.path())
        f.write('Log:\n')
        f.write('%s\n' % self.model.log())
        f.close()

    def file(self, file=None):
        """The path of the file to dump the Model to."""
        if file is not None: self._file = file
        return self._file
