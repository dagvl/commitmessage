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

        # Markers to tell us when we hit a new diff
        markers = ['Modified', 'Added', 'Copied', 'Deleted', 'Property changes on']

        # Recontruct each diff by parsing through the output of svnlook line by line
        diffs = []
        partialDiff = None

        #A marker word after a "____" line is a change in a property and shouldn't be added as a change
        #in a file. InProperty keeps track of this. If it's 0 this is a normal line, any larger 
        #and it's a property line.
        inProperty = 1
        for line in self.getDiffLines():
            inProperty = max(0, inProperty-1)
            if line == "___________________________________________________________________\n":
                inProperty = 2

            # Look for Modified:, Added:, etc.
            if line[0:line.find(':')] in markers and not inProperty > 0:
                # Handle starting a new diff
                partialDiff = [line]
                diffs.append(partialDiff)
            elif partialDiff:
                partialDiff.append(line)

        if len(diffs) == 0:
            for file in self.model.files():
                file.delta = '<Unavailable>'
                file.diff = ''

        # And finally parse through the diffs and save them into our tree of changes
        for diff in diffs:
            # Use [:-1] to leave of the trailing \n
            start = diff[0].find(': ') + 2
            stop = diff[0].find('(') - 1 # -1 ignores the space before the paren
            if stop == -2: stop = len(diff[0])

            filePath = '/' + diff[0][:-1][start:stop]

            # This could be a file or a directory - going ahead with the .file()
            # call for most directories is fine as it will just return null.
            #
            # Howeever, root / will exception out as an invalid file path so
            # just special case it
            if filePath == '/':
                file = None
            else:
                file = self.model.file(self.prefix + filePath)

            # Maybe its a directory
            if file:
                isFile = True
            else:
                file = self.model.directory(self.prefix + filePath + '/')
                isFile = False

            if not diff[0].startswith('Property changes on:'):
                file.delta, file.diff = self._parse_diff(diff)
            else:
                if file.diff:
                    # Only files will already have a diff set
                    file.diff = file.diff + '\n\n' + ''.join(diff)
                else:
                    # If the 'Property changes on' line is here without a
                    # file.diff, that file.diff will never come because it would
                    # have been printed before us
                    if isFile:
                        sep = '===================================================================\n\n'
                        file.diff = ''.join([sep] + diff)
                        file.delta = '+0 -0'
                    else:
                        file.diff = ''.join(diff)

    def getDiffLines(self):
        """@return: a list of diff lines to process, if under the summary threshold"""

        #Workaround for SVN issue 1789
        tempDir = self.repoPath + '/cm_temp'
        tempFile = tempDir + '/' + self.rev + '.diff'

        #Ensure the temp directory exists in the repo
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)

        #Delete any files of the same name
        if os.path.exists(tempFile):
            os.remove(tempFile)

        self._svnlook('diff', ' > ' + tempFile)

        # getSummaryThreshold returns -1 if the option is undefined (ergo, no summary)
        diff_lines = []
        if self.config.getSummaryThreshold() == -1 or os.stat(tempFile).st_size <= self.config.getSummaryThreshold():
            diff_file = open(tempFile, 'r')
            diff_lines = diff_file.readlines()
            diff_file.close()

        os.remove(tempFile)

        return diff_lines

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

    def _svnlook(self, command, opt_command=''):
        """@return: the lines ouput by the C{svnlook} command against the current repo and rev"""
        return execute('svnlook %s %s -r %s %s' % (command, self.repoPath, self.rev, opt_command))

