#!/usr/bin/python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""The controller and utils for the Subversion SCM (http://subversion.tigris.org)."""

import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Controller, File, Directory
from commitmessage.util import execute

class SvnController(Controller):
    """Uses 'svnlook' to pull data from svn repositories."""

    def populateModel(self):
        """Fill out the model."""
        self.repoPath = self.argv[1]
        self.rev = self.argv[2]

        lines = self.svnlook('info')
        self.model.user(lines[0][:-1])
        self.model.log(lines[3])

        changes = self.svnlook('changed')
        for change in changes:
            action = self.getAction(change[0])
            target = change[4:-1]
            if target != '/' and target[0] != '/':
                target = '/' + target
            if target.endswith('/'):
                self.handleDirectory(action, target)
            else:
                self.handleFile(action, target)
        self.saveDiffs(self.svnlook('diff'))

    def getAction(self, changeLetter):
        """Converts single action abbreviations (e.g. U/A/D) to commitmessage's
        fuller versions (e.g. modified/added/removed).  Raises a CmException if
        the conversion fails."""
        if changeLetter == 'A':
            return 'added'
        elif changeLetter == 'D':
            return 'removed'
        elif changeLetter == 'U':
            return 'modified'
        else:
            raise CmException, "The change letter '%s' was invalid." % changeLetter

    def handleDirectory(self, action, path):
        """Adds directories to the model."""
        dir = self.model.directory(path)
        dir.action(action)

    def handleFile(self, action, path):
        """Adds files to the model."""
        # Remove the name of the file from the path
        parts = path.split('/')
        name = parts[-1]
        dirPath = '/' + '/'.join(parts[1:-1])

        dir = self.model.directory(dirPath)
        f = File(name, dir, action)

    def saveDiffs(self, lines):
        """Calls svnlook diff and parses out the diff information."""
        fileDiffs = []
        currentDiff = None
        lastLine = lines[0]
        for line in lines[1:]:
            if line == '==============================================================================\n':
                if currentDiff is not None:
                    fileDiffs.append(currentDiff)
                currentDiff = [lastLine]
            else:
                currentDiff.append(lastLine)
            lastLine = line
        currentDiff.append(lastLine)
        fileDiffs.append(currentDiff)

        for diff in fileDiffs:
            # Use [:-1] to leave of the trailing \n
            filePath = '/' + diff[0][:-1].split(' ')[-1]
            text = ''
            added = 0
            removed = 0
            for line in diff[1:]:
                if len(line) > 0:
                    if line[0] == '+' and not line[0:3] == '+++':
                        added = added + 1
                    elif line[0] == '-' and not line[0:3] == '---':
                        removed = removed + 1
                text = text + line
            f = self.model.file(filePath)
            f.diff(text)
            f.delta('+%s -%s' % (added, removed))

    def svnlook(self, command):
        """Returns the lines ouput by the svnlook command against the current
        repo and rev."""
        return execute('svnlook %s %s -r %s' % (command, self.repoPath, self.rev))
