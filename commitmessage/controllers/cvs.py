#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""The controller and utils for the CVS SCM (http://www.cvshome.org)."""

import os
import cPickle
import re
import sys

from commitmessage.framework import Controller, Directory, File, Model
from commitmessage.util import execute

def cvs_status(file):
    """Returns rev and delta for file."""
    rev, delta = '', ''
    p = re.compile(r"^[ \t]*Repository revision")
    q = re.compile(r"^date:")
    for line in execute('cvs -Qn status %s' % file):
        if p.search(line):
            rev = line.strip().split('\t')[1]
            break
    if rev != '':
        for line in execute('cvs -Qn log -r%s %s' % (rev, file)):
            if q.search(line):
                line = line.strip()
                line = re.sub(re.compile(r"^.*;"), '', line)
                line = re.sub(re.compile(r"^[\s]+lines:"), '', line)
                delta = line.strip()
    return rev, delta

def cvs_previous_rev(rev):
    """Return the revision previous to this."""
    prev = ''
    match = re.compile(r"^(.*)\.([0-9]+)$").search(rev)
    if match != None:
        prev = '%s.%s' % (match.group(1), int(match.group(2)) - 1)
        # Truncate if on first rev of branch
        p = re.compile(r"\.[0-9]+\.0$")
        if p.search(prev):
            prev = re.sub(p, '', prev)
    return prev

def cvs_diff(file, rev):
    """Performs a diff on the given file."""
    p = re.compile(r"\.(?:pdf|gif|jpg|mpg)$", re.I)
    if (p.search(file)):
        return '<<Binary file>>'

    diff, lines = '', []
    if rev == '1.1':
        lines = execute('cvs -Qn update -p -r1.1')
        diff = 'Index %s\n===================================================================\n' % file
    else:
        lines = execute('cvs -Qn diff -u -r%s -r %s %s' % (cvs_previous_rev(rev), rev, file))
    for line in lines:
        diff = diff + line
    return diff

class CvsController(Controller):
    """Translates CVS loginfo/commitinfo information into the Model."""

    FILE_PREFIX = ''
    """A unique prefix to avoid multiple processes stepping on each other's toes.

    The Unix getpgrp command is used as Cvs will invoke multiple process
    instances of main.py for each directory's loginfo and commitinfo, but the
    pgrp will remain the same for each spawned process."""

    LAST_DIRECTORY_FILE = ''
    """The file to store the last directory that commitinfo was executed in.
    Must be assigned to after the FILE_PREFIX has been set in __init__."""

    def __init__(self, config, argv, stdin):
        """Sets the 'done' attribute to false so we handle the multiple
        executions CVS does against main.py."""
        try:
            CvsController.FILE_PREFIX = '#cvs.%s.' % os.getpgrp()
        except AttributeError:
            sys.stderr.write('WARNING, the CvsController is designed only to run on Unix.')
            CvsController.FILE_PREFIX = '#cvs.'
        CvsController.LAST_DIRECTORY_FILE = '%s/%slastdir' % (Controller.TMPDIR, CvsController.FILE_PREFIX)
        Controller.__init__(self, config, argv, stdin)
        self.model.user(os.getenv('USER') or os.getlogin())

    def _populateModel(self):
        """Read in the information."""
        if len(self.argv) > 2:
            self._doCommitInfo()
        else:
            self._doLogInfo()

    def _stopProcessForNow(self):
        """Return whether we should stop and wait for CVS to re-execute main.py
        on the next directory of the commit."""
        if self._isLastDirectoryOfCommit():
            return 0
        else:
            return 1

    def _isLastDirectoryOfCommit(self):
        """Return whether the current directory is the last directory of the commit."""
        # Just stop if currentDirectory doesn't exist (this is commitinfo)
        if not hasattr(self, 'currentDirectory'):
            return 0
        # Also last dir if this is a new directory exec of loginfo
        if len(self.currentDirectory.files()) == 0:
            return 1
        # Simple cache to avoid re-parsing the file
        if hasattr(self, '_done'):
            return self._done
        pathToMatch = '%s%s' % (os.environ['CVSROOT'], self.currentDirectory.path())
        matched = 0
        f = file(CvsController.LAST_DIRECTORY_FILE, 'r')
        for line in f.readlines():
            if line == pathToMatch:
                matched = 1
        f.close()

        # Cache the value
        self._done = matched

        return matched

    def _doCommitInfo(self):
        """Executed first and saves the current directory name to
        LAST_DIRECTORY_FILE so that doLogInfo will know when it is done (it will
        be done with it's on the same directory as the last one that
        doCommitInfo saved)."""
        f = file(CvsController.LAST_DIRECTORY_FILE, 'w')
        f.write(self.argv[1])
        f.close()

    def _doLogInfo(self):
        """Executed after all of the directories' commitinfos have ran, so we
        know the last directory and can start to build the Model of commit
        information."""
        temp = self.argv[1].split(' ')
        currentDirectoryName = '/' + temp[0]
        directoryFiles = temp[1:]

        # Creates self.currentDirectory and self.logLines
        self.parseLoginfoStdin(currentDirectoryName)

        # Check for a new directory commit
        if len(directoryFiles) == 3 \
            and directoryFiles[0] == '-' \
            and directoryFiles[1] == 'New' \
            and directoryFiles[2] == 'directory':
            self.currentDirectory.action('added')

        self.fillInValues()

        if self._isLastDirectoryOfCommit():
            self._parseLogLinesIntoModel()
            self.model.addDirectory(self.currentDirectory)
        else:
            self._saveDirectory()

    def _parseLogLinesIntoModel(self):
        """Saves the logLines found on stdin into the model."""
        while len(self.logLines) > 0 and self.logLines[0] == '':
            del self.logLines[0]
        while len(self.logLines) > 0 and self.logLines[-1] == '':
            del self.logLines[-1]
        # If a new directory commit, only 1 line is given
        if len(self.currentDirectory.files()) == 0:
            self.model.log(self.logLines[0])
        else:
            self.model.log('\n'.join(self.logLines))

    def _saveDirectory(self):
        """Pickles the given directory off to TMPDIR/FILE_PREFIXdir-path."""
        path = '%s/%s%s' % (
            Controller.TMPDIR,
            CvsController.FILE_PREFIX,
            self.currentDirectory.path().replace('/', '-'))
        f = file(path, 'w')
        cPickle.dump(self.currentDirectory, f)
        f.close()

    def _fillInValues(self):
        """Goes through each file and fills in the missing rev/delta/diff information."""
        for file in self.currentDirectory.files():
            rev, delta = cvs_status(file.name())
            file.rev(rev)
            file.delta(delta)
            if file.action() == 'added' or file.action() == 'modified':
                file.diff(cvs_diff(file.name(), rev))

    def _parseLoginfoStdin(self, directoryName):
        """Reads in the loginfo text from self.stdin and retreives the
        corresponding diff/delta information for each file."""
        self.logLines = []
        self.currentDirectory = Directory(directoryName + '/')

        STATE_NONE = 0
        STATE_MODIFIED = 1
        STATE_ADDED = 2
        STATE_REMOVED = 3
        STATE_LOG = 4
        state = STATE_NONE

        m = re.compile(r"^Modified Files")
        a = re.compile(r"^Added Files")
        r = re.compile(r"^Removed Files")
        l = re.compile(r"^Log Message")
        b = re.compile(r"Revision\/Branch:")
        for line in self.stdin.xreadlines():
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
                continue

            files = line.split(' ')
            if (state == STATE_MODIFIED):
                for name in files: File(name, self.currentDirectory, 'modified')
            if (state == STATE_ADDED):
                for name in files: File(name, self.currentDirectory, 'added')
            if (state == STATE_REMOVED):
                for name in files: File(name, self.currentDirectory, 'removed')
            if (state == STATE_LOG):
                self.logLines.append(line)

    def _executeViews(self):
        """Over-ride the parent executeViews to re-build the model from the temporary files."""
        self._loadSavedDirectoriesIntoModel()
        # Carry on with executing the views
        Controller.executeViews(self)

    def _loadSavedDirectoriesIntoModel(self):
        """Re-loads the directories into the Model."""
        allFiles = os.listdir(Controller.TMPDIR)
        for name in allFiles:
            if name.startswith(CvsController.FILE_PREFIX):
                fullPath = '%s/%s' % (Controller.TMPDIR, name)
                if not name.endswith('lastdir'):
                    f = file(fullPath)
                    directory = cPickle.load(f)
                    f.close()
                    self.model.addDirectory(directory)
                os.remove(fullPath)

