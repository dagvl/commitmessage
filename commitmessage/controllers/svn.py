#!/usr/bin/python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""The controller and utils for the Subversion SCM (U{http://subversion.tigris.org})"""

import os
import sys

from commitmessage.model import Controller, File, Directory
from commitmessage.util import execute

class SvnController(Controller):
    """Uses C{svnlook} to pull data from svn repositories"""

    # A mapping from abbreviation to a better description.
    actions = { 'A': 'added', 'D': 'removed', 'U': 'modified' }

    def _populateModel(self):
        """Fills out the model by invoking C{svnlook}"""

        self.repoPath = self.argv[1]
        self.rev = self.argv[2]
        self.model.rev = self.rev

        # First, get the user and log message
        lines = self._svnlook('info')
        self.model.user = lines[0][:-1]
        self.model.log = ''.join(lines[3:]).strip()

        # Now build an initial tree of file and tree changes
        for line in self._svnlook('changed'):
            action = self.actions[line[0]]
            target = '/' + line[4:-1]

            if target.endswith('/'):
                directory = self.model.directory(target)
                directory.action = action
            else:
                parts = target.split('/')
                name = parts[-1]
                directoryPath = '/' + '/'.join(parts[0:-1]) + '/'

                file = File(name, self.model.directory(directoryPath), action)

        # And finally parse through the diffs and save them into our tree of changes
        diffs = []
        for line in self._svnlook('diff'):
            if line.startswith('Modified: ') or line.startswith('Added: ') or line.startswith('Copied: ') or line.startswith('Deleted: '):
                # Handle starting a new diff
                partialDiff = [line]
                diffs.append(partialDiff)
            else:
                partialDiff.append(line)

        for diff in diffs:
            # Use [:-1] to leave of the trailing \n
            filePath = '/' + diff[0][:-1].split(' ')[1]
            delta, text = self._parse_diff(diff)

            file = self.model.file(filePath)
            file.diff = text
            file.delta = delta

    def _parse_diff(self, diff):
        text = ''
        added = 0
        removed = 0
        for line in diff[1:-1]:
            if len(line) > 0:
                if line[0] == '+' and not line[0:4] == '+++ ':
                    added = added + 1
                elif line[0] == '-' and not line[0:4] == '--- ':
                    removed = removed + 1
            text = text + line

        # Handle copy without modification, with results in no diff
        if text == '':
            text = diff[0]

        return ('+%s -%s' % (added, removed), text)

    def _svnlook(self, command):
        """@return: the lines ouput by the C{svnlook} command against the current repo and rev"""
        return execute('svnlook %s %s -r %s' % (command, self.repoPath, self.rev))

