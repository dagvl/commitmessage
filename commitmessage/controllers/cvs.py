#!/usr/bin/env python
#
# commitmessage
# Copyright 2002, 2003 Stephen Haberman
#

"""
The controller and utils for the CVS SCM (http://www.cvshome.org).
"""

import os
import cPickle
import re
import sys

from commitmessage.model import Controller, Directory, File, Model
from commitmessage.util import execute

# The cvs_status and cvs_diff commands are executed in the ...working
# directory... either client side or server side, I forget which.

def cvs_status(file):
    """@return: the rev and delta for C{file} during a commit"""
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
    """@return: the revision previous to C{rev}."""
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
    """@return: the diff on the given file during a commit"""
    p = re.compile(r"\.(?:pdf|gif|jpg|mpg)$", re.I)
    if (p.search(file)):
        return '<<Binary file>>'

    diff, lines = '', []

    if rev == '1.1':
        lines = execute('cvs -Qn update -p -r1.1 %s' % file)
        diff = 'Index: %s\n===================================================================\n' % file
    else:
        lines = execute('cvs -Qn diff -u -r%s -r %s %s' % (cvs_previous_rev(rev), rev, file))

    diff = diff + ''.join(lines)

    if rev == '1.1':
        diff = diff + '\n'

    return diff

class CvsController(Controller):
    """Translates CVS loginfo/commitinfo information into the Model."""

    # A unique prefix to avoid multiple processes stepping on each other's toes.
    #
    # The Unix getpgrp command is used as Cvs will invoke multiple process
    # instances of main.py for each directory's loginfo and commitinfo, but the
    # pgrp will remain the same for each spawned process."""
    FILE_PREFIX = ''

    # The file to store the last directory that commitinfo was executed in. Must
    # be assigned to after the FILE_PREFIX has been set in __init__.
    LAST_DIRECTORY_FILE = ''

    def __init__(self, config, argv, stdin):
        """
        Sets the 'done' attribute to false so we handle the multiple executions
        CVS does of main.py (one per directory in the commit).
        """
        try:
            CvsController.FILE_PREFIX = '#cvs.%s.' % os.getpgrp()
        except AttributeError:
            sys.stderr.write('WARNING, the CvsController is designed only to run on Unix.')
            CvsController.FILE_PREFIX = '#cvs.'
        CvsController.LAST_DIRECTORY_FILE = '%s/%slastdir' % (Controller.TMPDIR, CvsController.FILE_PREFIX)

        Controller.__init__(self, config, argv, stdin)

        self.model.user = os.getenv('USER') or os.getlogin()
        self.removecvsmoduleprefix = 'yes'

    def removeCvsModulePrefix(self):
        if self.removecvsmoduleprefix == 'yes':
            return True
        else:
            return False

    def _populateModel(self):
        """Read in the information."""
        if len(self.argv) > 2:
            self._doCommitInfo()
        else:
            self._doLogInfo()

    def _stopProcessForNow(self):
        """
        @return: whether we should stop and wait for CVS to re-execute main.py
        on the next directory of the commit.
        """
        # If in commitinfo, always stop
        if not hasattr(self, 'currentDirectory'):
            return True

        # If in loginfo, stop if we're not on the last directory
        if not self._isLastDirectoryOfCommit():
            return True

        return False

    def _isLastDirectoryOfCommit(self):
        """@return: whether the current directory is the last directory of the commit"""
        # Last dir if this is a new directory exec of loginfo
        if len(self.currentDirectory.files) == 0:
            return True

        f = file(CvsController.LAST_DIRECTORY_FILE, 'r')
        fullPath = f.readlines()[0]
        f.close()

        lastColon = os.environ['CVSROOT'].rindex(':')
        rootPath = os.environ['CVSROOT'][lastColon+1:]

        # Standardize to have an end slash
        if not rootPath.endswith('/'):
            rootPath = rootPath + '/'

        if not fullPath.startswith(rootPath):
            return False
        else:
            # len(rootPath)-1 as we want to keep a beginning slash
            pathWithModule = fullPath[len(rootPath)-1:]

        if not pathWithModule.endswith(self.currentDirectory.path):
            return False
        else:
            endAt = len(pathWithModule) - len(self.currentDirectory.path)
            leftOverModule = pathWithModule[:endAt] + '/'

        # If the cvs module was in the currentDirectory.path and nothing was left, we're good
        if self.removeCvsModulePrefix() and leftOverModule == '/':
            return True

        # Else we want only the module to be left: a starting /, ending /, and no other /
        if leftOverModule[1:-1].count('/') == 0:
            return True

        # There was a slash in the left over part, so this is not the right directory
        return False

    def _doCommitInfo(self):
        """
        Executed first and saves the current directory name to
        LAST_DIRECTORY_FILE so that doLogInfo will know when it is done (it will
        be done with it's on the same directory as the last one that
        doCommitInfo saved).
        """
        f = file(CvsController.LAST_DIRECTORY_FILE, 'w')

        fullPath = self.argv[1]
        if not fullPath.endswith('/'):
            fullPath = fullPath + '/'

        f.write(fullPath)
        f.close()

    def _doLogInfo(self):
        """
        Executed after all of the directories' commitinfos have ran, so we know
        the last directory and can start to build the Model of commit
        information.
        """
        temp = self.argv[1].split(' ')
        directoryPath = '/' + temp[0] + '/'
        directoryFiles = temp[1:]

        # Handle removing the module prefix from the directory name
        if self.removeCvsModulePrefix():
            secondSlash = directoryPath.find('/', 1)
            directoryPath = directoryPath[secondSlash:]

        self.currentDirectory = Directory(directoryPath)

        # Also creates self.logLines
        self._parseLoginfoStdinIntoFiles()

        # Check for a new directory commit
        if len(directoryFiles) == 3 \
            and directoryFiles[0] == '-' \
            and directoryFiles[1] == 'New' \
            and directoryFiles[2] == 'directory':
            self.currentDirectory.action('added')

        self._fillInValues()

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
        if len(self.currentDirectory.files) == 0:
            self.model.log = self.logLines[0]
        else:
            self.model.log = '\n'.join(self.logLines)

    def _saveDirectory(self):
        """Pickles the given directory off to TMPDIR/FILE_PREFIX directory."""
        path = '%s/%s%s' % (
            Controller.TMPDIR,
            CvsController.FILE_PREFIX,
            self.currentDirectory.path.replace('/', '-'))
        f = file(path, 'w')
        cPickle.dump(self.currentDirectory, f)
        f.close()

    def _fillInValues(self):
        """Goes through each file and fills in the missing rev/delta/diff information."""
        for file in self.currentDirectory.files:
            (file.rev, file.delta) = cvs_status(file.name)

            if file.action == 'added' or file.action == 'modified':
                file.diff = cvs_diff(file.name, file.rev)

            if file.action == 'added':
                # the cvs_diff does not include a delta on additions
                if file.action == 'added':
                    file.delta = '+%s -0' % (file.diff.count('\n') - 2)

    def _parseLoginfoStdinIntoFiles(self):
        """
        Reads in the loginfo text from self.stdin and retreives the
        corresponding diff/delta information for each file.
        """
        self.logLines = []

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
        """Override the parent executeViews to re-build the model from the temporary files."""
        self._loadSavedDirectoriesIntoModel()
        # Carry on with executing the views
        Controller._executeViews(self)

    def _loadSavedDirectoriesIntoModel(self):
        """Reloads the directories into the Model."""
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

