#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""The controller and utils for the CVS SCM (http://www.cvshome.org)."""

import fileinput
import os
import re
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Controller, Directory, File, Model

class CvsController(Controller):
    """Translates CVS loginfo/commitinfo information into the Model."""

    FILE_PREFIX = '#cvs.%s.' % os.getpid()
    """A unique prefix to avoid multiple processes stepping on each other's toes."""

    LAST_DIRECTORY_FILE = '%s/%slastdir' % (Controller.TMPDIR, FILE_PREFIX)
    """The file to store the last directory that commitinfo was executed in."""

    def __init__(self, config, argv, stdin):
        """Sets the 'done' attribute to false so we handle the multiple
        executions CVS does against main.py."""
        Controller.__init__(self, config, argv, stdin)
        self.done = 0

    def process(self):
        """Read in the information."""
        if len(self.argv) > 2:
            self.doCommitInfo()
        else:
            self.doLogInfo()

    def stopProcessForNow(self):
        """Return whether doLogInfo has said it's okay to stop (e.g. it has
        reached the last directory recorded by doCommitInfo)."""
        return self.done

    def doCommitInfo(self):
        """Executed first and saves the current directory name to
        LAST_DIRECTORY_FILE so that doLogInfo will know when it is done (it will
        be done with it's on the same directory as the last one that
        doCommitInfo saved)."""
        f = file(CvsController.LAST_DIRECTORY_FILE, 'w')
        f.write(self.argv[1])
        f.close()

    def doLogInfo(self):
        """Executed after all of the directories' commitinfos have ran, so we
        know the last directory and can start to build the Model of commit
        information."""

        self.saveCurrentDirectoryChangesToFile(self.argv[1])

    def saveCurrentDirectoryChangesToFile(self, arg):
        """Parses in the current input to loginfo."""
        temp = arg.split(' ')
        self.logLines = []
        self.currentDirectory = Directory(temp[0])

        STATE_NONE = 0
        STATE_MODIFIED = 1
        STATE_ADDED = 2
        STATE_REMOVED = 3
        STATE_LOG = 4
        state = STATE_NONE

        # Check for a new directory commit
        files = temp[1:]
        if len(files) == 3 and files[0] == '-' and files[1] == 'New' and files[2] == 'directory'):
            currentDirectory.action('added')

        m = re.compile(r"^Modified Files")
        a = re.compile(r"^Added Files")
        r = re.compile(r"^Removed Files")
        l = re.compile(r"^Log Message")
        b = re.compile(r"Revision\/Branch:")
        for line in self.stdin.readlines():
            line = line.strip()
            if b.search(line):
                line = re.sub(b, '', line)
                branchLines.append(line)
            if m.search(line):
                state = STATE_MODIFIED
                continue
            if a.search(line):
                state = STATE_ADDED
                continue
            if r.search(line):
                state = STATE_REMOVED
                continue
            if l.search(line):
                state = STATE_LOG

            files = line.split(' ')
            if (state == STATE_MODIFIED):
                for name in files: File(name, currentDirectory, 'modified')
            if (state == STATE_ADDED): 
                for name in files: File(name, currentDirectory, 'added')
            if (state == STATE_REMOVED): 
                for name in files: File(name, currentDirectory, 'removed')
            if (state == STATE_LOG):
                self.logLines.append(line)



if __name__ == '__name__':
    print('hello kitty')
