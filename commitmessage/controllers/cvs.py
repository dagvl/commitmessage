#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""
The controller and utils for the CVS SCM (U{http://www.cvshome.org})
"""

import os
import pickle
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
    for line in execute('cvs -Qnf status "%s"' % file):
        if p.search(line):
            rev = line.strip().split('\t')[1]
            break
    if rev != '':
        for line in execute('cvs -Qnf log -r%s "%s"' % (rev, file)):
            if q.search(line):
                line = line.strip()
                line = re.sub(re.compile(r"^.*;"), '', line)
                line = re.sub(re.compile(r"^[\s]+lines:"), '', line)
                delta = line.strip()
    return rev, delta

def cvs_previous_rev(rev):
    """@return: the revision previous to C{rev}"""
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
    """@return: the C{(delta,diff)} on the given L{File} during a commit"""
    p = re.compile(r"\.(?:pdf|gif|jpg|mpg)$", re.I)
    if (p.search(file.name)):
        return '+0 -0', '===================================================================\n<<Binary file>>\n'
    if file.action == 'removed':
        return '+0 -0', '===================================================================\n'

    diff, lines = '', []

    if rev == '1.1':
        lines = execute('cvs -Qnf update -p -r1.1 "%s"' % file.name)
        diff = 'Index: %s\n===================================================================\n' % file.name
        added, removed = 0, 0
    else:
        lines = execute('cvs -Qnf diff -u -r%s -r %s "%s"' % (cvs_previous_rev(rev), rev, file.name))
        added, removed = -1, -1

    for line in lines:
        if rev == '1.1':
            added = added + 1
        elif len(line) > 0:
            if line[0] == '+':
                added = added + 1
            elif line[0] == '-':
                removed = removed + 1
        diff = diff + line

    if rev == '1.1':
        diff = diff + '\n'

    return '+%s -%s' % (added, removed), diff

class CvsController(Controller):
    """Translates CVS loginfo/commitinfo information into the model"""

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
        """Initializes up the L{FILE_PREFIX}, L{LAST_DIRECTORY_FILE}, and other variables"""
        try:
            CvsController.FILE_PREFIX = '#cvs.%s.' % os.getpgrp()
        except AttributeError:
            sys.stderr.write('WARNING, the CvsController is designed only to run on Unix.')
            CvsController.FILE_PREFIX = '#cvs.'
        CvsController.LAST_DIRECTORY_FILE = '%s/%slastdir' % (Controller.TMPDIR, CvsController.FILE_PREFIX)

        Controller.__init__(self, config, argv, stdin)

        self.model.user = os.getenv('USER') or os.getlogin()
        # Set in _doLogInfo
        # self.model.repo = ...

    def _populateModel(self):
        """Performs L{_doCommitInfo} (done first for each directory) or L{_doLogInfo} (done last for each directory)"""
        if len(self.argv) > 2:
            self._doCommitInfo()
        else:
            self._doLogInfo()

    def _stopProcessForNow(self):
        """@return: C{True} if we're in L{_doCommitInfo} or not the last directory for which L{_doLogInfo} will be invoked"""
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
        if not self.addRepoPrefix() and leftOverModule == '/':
            return True

        # Else we want only the module to be left: a starting /, ending /, and no other /
        if leftOverModule[1:-1].count('/') == 0:
            return True

        # There was a slash in the left over part, so this is not the right directory
        return False

    def _doCommitInfo(self):
        """Saves the current directory name to C{LAST_DIRECTORY_FILE} so that
        L{_doLogInfo} will know when it is done (when it's on the same directory
        as the last one L{_doCommitInfo} saved)

        Executed for each directory in the commit before any L{_doLogInfo}s are
        called.
        """
        f = file(CvsController.LAST_DIRECTORY_FILE, 'w')

        fullPath = self.argv[1]
        if not fullPath.endswith('/'):
            fullPath = fullPath + '/'

        f.write(fullPath)
        f.close()

    def _doLogInfo(self):
        """Starts building the model if this is the last L{_doLogInfo} of the commit

        Executed for each directory in the commit after all of the
        L{_doCommitInfo}s are called.
        """
        temp = self.argv[1].split(' ')
        directoryPath = '/' + temp[0] + '/'
        directoryFiles = temp[1:]

        # Handle removing the module prefix from the directory name
        secondSlash = directoryPath.find('/', 1)
        # Go ahead and set self.model.repo now
        self.model.repo = directoryPath[1:secondSlash]
        if not self.addRepoPrefix():
            directoryPath = directoryPath[secondSlash:]

        self.currentDirectory = Directory(directoryPath)

        # Also creates self.logLines
        self._parseLoginfoStdinIntoFiles()

        # Check for a new directory commit
        if len(directoryFiles) == 3 \
            and directoryFiles[0] == '-' \
            and directoryFiles[1] == 'New' \
            and directoryFiles[2] == 'directory':
            self.currentDirectory.action = 'added'

        self._fillInValues()

        if self._isLastDirectoryOfCommit():
            self._parseLogLinesIntoModel()
            self.model.addDirectory(self.currentDirectory)
        else:
            self._saveDirectory()

    def _parseLogLinesIntoModel(self):
        """Saves the log lines found on C{stdin} into the model"""
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
        """Pickles the current L{Directory} off to the C{TMPDIR/FILE_PREFIX} directory"""
        path = '%s/%s%s' % (
            Controller.TMPDIR,
            CvsController.FILE_PREFIX,
            self.currentDirectory.path.replace('/', '-'))
        f = file(path, 'w')
        pickle.dump(self.currentDirectory, f)
        f.close()

    def _fillInValues(self):
        """Goes through each file in this execution's directory and fills in the missing rev/delta/diff information"""
        for file in self.currentDirectory.files:
            (file.rev, file.delta) = cvs_status(file.name)

            if file.action == 'added' or file.action == 'modified' or file.action == 'removed':
                file.delta, file.diff = cvs_diff(file, file.rev)


    def _parseLoginfoStdinIntoFiles(self):
        """Reads in the loginfo text from C{stdin} and parses the file information into L{File}s"""
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
        for line in self.stdin:
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
        """Overrides the parent C{_executeViews} to r-build the model with all of the temporary files"""
        self._loadSavedDirectoriesIntoModel()
        # Carry on with executing the views
        Controller._executeViews(self)

    def _loadSavedDirectoriesIntoModel(self):
        """Reloads the pickled L{Directory}s into the model"""
        allFiles = os.listdir(Controller.TMPDIR)
        for name in allFiles:
            if name.startswith(CvsController.FILE_PREFIX):
                fullPath = '%s/%s' % (Controller.TMPDIR, name)
                if not name.endswith('lastdir'):
                    f = file(fullPath)
                    directory = pickle.load(f)
                    f.close()
                    self.model.addDirectory(directory)
                os.remove(fullPath)

