#!/usr/bin/python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""The controller and utils for the Subversion SCM (U{http://subversion.tigris.org})"""

import os
import sys

from commitmessage.model import Controller, File, Directory
from commitmessage.util import execute

class SvnController(Controller):
    """Uses C{svnlook} to pull data from svn repositories"""

    # A mapping from abbreviation to a better description.
    actions = { 'A': 'added', 'D': 'removed', 'U': 'modified', '_': 'modified' }

    def _populateModel(self):
        """Fills out the model by invoking C{svnlook}"""

        self.repoPath = self.argv[1]
        self.rev = self.argv[2]
        self.model.rev = self.rev
        self.model.repo = os.path.split(self.repoPath)[-1]
        self.prefix = (self.addRepoPrefix() and ('/' + self.model.repo)) or ''

        # First, get the user and log message
        lines = self._svnlook('info')
        self.model.user = lines[0][:-1]
        self.model.log = ''.join(lines[3:]).strip()

        # Now build an initial tree of file and tree changes
        for line in self._svnlook('changed'):
            action = self.actions[line[0]]
            target = '/' + line[4:-1]

            if target.endswith('/'):
                directory = self.model.directory(self.prefix + target)
                directory.action = action
            else:
                parts = target.split('/')
                name = parts[-1]
                directoryPath = '/' + '/'.join(parts[0:-1]) + '/'

                file = File(name, self.model.directory(self.prefix + directoryPath), action)

        markers = ['Modified', 'Added', 'Copied', 'Deleted', 'Property changes on']

        # And finally parse through the diffs and save them into our tree of changes
        diffs = []
        partialDiff = None
        for line in self._svnlook('diff'):
            # Look for Modified:, Added:, etc.
            if line[0:line.find(':')] in markers:
                # Handle starting a new diff
                partialDiff = [line]
                diffs.append(partialDiff)
            elif partialDiff:
                partialDiff.append(line)

        for diff in diffs:
            # Use [:-1] to leave of the trailing \n
            start = diff[0].find(': ') + 2
            stop = diff[0].find('(') - 1 # -1 ignores the space before the paren
            if stop == -2: stop = len(diff[0])

            filePath = '/' + diff[0][:-1][start:stop]

            #f not diff[0].startswith('Property changes on:'):
            #   filePath = '/' + diff[0][:-1].split(' ')[1]
            #lse:
            #   # Property changes line puts the file name somewhere else
            #   filePath = '/' + diff[0][:-1].split(' ')[-1]

            file = self.model.file(self.prefix + filePath)

            if not diff[0].startswith('Property changes on:'):
                file.delta, file.diff = self._parse_diff(diff)
            else:
                if file.diff:
                    file.diff = file.diff + '\n\n' + ''.join(diff)
                else:
                    # If the 'Property changes on' line is here without a
                    # file.diff, that file.diff will never come because it would
                    # have been printed before us
                    sep = '===================================================================\n\n'
                    file.diff = ''.join([sep] + diff)
                    file.delta = '+0 -0'

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

