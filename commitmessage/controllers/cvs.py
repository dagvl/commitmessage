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

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from commitmessage.framework import Controller, Directory, File, Model

def cvs_status(file):
    """Returns rev and delta for file."""
    rev, delta = '', ''
    p = re.compile(r"^[ \t]*Repository revision")
    q = re.compile(r"^date:")
    pipeIn, pipeOut = os.popen2('cvs -Qn status %s' % file, 'r')
    for line in pipeOut.readlines():
        if p.search(line):
            rev = line.strip().split('\t')[1]
            break
    pipeIn.close()
    pipeOut.close()
    if rev != '':
        pipeIn, pipeOut = os.popen2('cvs -Qn log -r%s %s' % (rev, file), 'r')
        for line in pipeOut.readlines():
            if q.search(line):
                line = line.strip()
                line = re.sub(re.compile(r"^.*;"), '', line)
                line = re.sub(re.compile(r"^[\s]+lines:"), '', line)
                delta = line.strip()
        pipeIn.close()
        pipeOut.close()
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

    prev = cvs_previous_rev(rev)
    diff, pipeIn, pipeOut = '', None, None

    if rev == '1.1':
        pipeIn, pipeOut = os.popen2('cvs -Qn update -p -r1.1')
        diff = 'Index %s\n===================================================================\n' % file
    else:
        pipeIn, pipeOut = os.popen2('cvs -Qn diff -u -r%s -r %s %s' % (prev, rev, file))

    for line in pipeOut.readlines():
        diff = diff + line

    pipeIn.close()
    pipeOut.close()

    return diff

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

    def populateModel(self):
        """Read in the information."""
        if len(self.argv) > 2:
            self.doCommitInfo()
        else:
            self.doLogInfo()

    def stopProcessForNow(self):
        """Return whether doLogInfo has said it's okay to stop (e.g. it has
        reached the last directory recorded by doCommitInfo)."""
        # Just stop if currentDirectory doesn't exist
        if not self.__dict__.has_key('currentDirectory'):
            return 1

        pathToMatch = '%s%s' % (os.environ['CVSROOT'], self.currentDirectory.path())
        matched = 0
        f = file(CvsController.LAST_DIRECTORY_FILE, 'r')
        for line in f.readlines():
            print 'lastdir: %s' % line
            print 'pathtom: %s' % pathToMatch
            if line == pathToMatch:
                matched = 1
        f.close()

        if matched:
            return 0
        else:
            return 1

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
        self.saveDirectory()

    def saveDirectory(self):
        """Pickles the given directory off to TMPDIR/FILE_PREFIXdir-path."""
        path = '%s/%s%s' % (
            Controller.TMPDIR,
            CvsController.FILE_PREFIX,
            self.currentDirectory.path().replace('/', '-'))
        f = file(path, 'w')
        cPickle.dump(self.currentDirectory, f)
        f.close()

    def fillInValues(self):
        """Goes through each file and fills in the missing rev/delta/diff information."""
        for file in self.currentDirectory.files():
            rev, delta = cvs_status(file.name())
            file.rev(rev)
            file.delta(delta)
            if file.action() == 'added' or file.action() == 'modified':
                file.diff(cvs_diff(file.name(), rev))

    def parseLoginfoStdin(self, directoryName):
        """Reads in the loginfo text from self.stdin and retreives the
        corresponding diff/delta information for each file."""
        self.logLines = []
        self.currentDirectory = Directory(directoryName)

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

            files = line.split(' ')
            if (state == STATE_MODIFIED):
                for name in files: File(name, self.currentDirectory, 'modified')
            if (state == STATE_ADDED): 
                for name in files: File(name, self.currentDirectory, 'added')
            if (state == STATE_REMOVED): 
                for name in files: File(name, self.currentDirectory, 'removed')
            if (state == STATE_LOG):
                self.logLines.append(line)

    def executeViews(self):
        """Over-ride the parent executeViews to re-build the model from the
        temporary files."""
        self.loadSavedDirectoriesIntoModel()
        # Carry on with executing the views
        Controller.executeViews(self)

    def loadSavedDirectoriesIntoModel(self):
        """Re-loads the directories into the Model."""
        allFiles = os.listdir(Controller.TMPDIR)
        for name in allFiles:
            if name.startswith(CvsController.FILE_PREFIX) and not name.endswith('lastdir'):
                fullPath = '%s/%s' % (Controller.TMPDIR, name)

                f = file(fullPath)
                directory = cPickle.load(f)
                f.close()

                self.model.addDirectory(directory)

                os.remove(fullPath)
