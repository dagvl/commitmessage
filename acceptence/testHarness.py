#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha2
# Copyright 2002, 2003 Stephen Haberman
#

"""A harness to test each of the XML file workflows for each controller and each view."""

import os
import sys
from xml.dom import minidom

sys.path.append('../')

import commitmessage.controllers.svn
import commitmessage.controllers.cvs

class ControllerFacade:
    """Wraps the interface to add/remove/changes files and directories in terms of each concrete repository."""

class Harness:
    """A class to wrap the test execution context; creates repository, executes the views, and compares the results."""

    def __init__(self):
        self.facades = []

    def addFacade(self, facade):
        """A wrapper to SCM-specific repository commands."""
        self.facades.append(facade)

    def run(self, cases):
        """Runs XML test cases."""
        for case in cases:
            self._runCase(case)

    def _runCase(self, case):
        """Runs an XML test case."""

        for facade in self.facades:
            """Each execution of the test case gets its own repository."""
            facade.createRepository()

            for commit in case.commits:
                """Let the case do its stuff."""
                commit.doChanges(facade)

                """Tell the facade to commit, which will 'commit' and have the controller executed."""
                facade.commit()

                """Check the results."""
                for view in case.views():
                    if view.contents != facade.view(view.name):
                        print 'Error:'
                        print 'Expected:'
                        print view.contents
                        print 'Actual:'
                        print facade.view(view.name)

            """We're done with this test case, so remove the repository."""
            facade.destoryRepository()

class Case:
    """A class to wrap the XML workflow files."""

    def __init__(self, fileName):
        """Init the test around an XML workflow file."""
        self.commits = []

        self.xmldoc = minidom.parse(file(fileName)).documentElement
        for commit in self.xmldoc.getElementsByTagName("commit"):
            self.commits.append(Commit(commit))

    def commits(self):
        """Returns the commits that this case wants to do."""
        return self.commits

class Commit:
    """A class to wrap a series of changes to a working directory."""

    def __init__(self, commitElement):
        """Initializes the object from the XML element."""
        self.commitElement = commitElement

    def doChanges(self, facade):
        """Loops through all of the changes for this commit."""
        for e in self.commitElement.childNodes:
            if e.nodeType == e.ELEMENT_NODE and e.tagName != 'view':
                # The args to pass to the function
                args = []

                # Each attribute is an argument, in order
                for key in e.attributes.keys():
                    args.append(e.attributes[key].value)

                # The text is an argument, too
                for node in e.childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        args.append(node.data)

                print args

                # Call the function
                getattr(facade, e.tagName)(*args)

    def views(self):
        """Returns the views that are expected by this commit, viewName: results."""

class CvsFacade:

    def createRepository(self):
        pass

class SvnFacade:

    def __init__(self):
        self.repoDir = '%s/temp-svn-repo' % os.getcwd().replace('\\', '/')
        self.workingDir = '%s/temp-svn-wd' % os.getcwd().replace('\\', '/')

    def _execsvn(self, cmd):
        """Executes cmd in the working directory."""
        os.chdir(self.workingDir)
        _exec(cmd)
        os.chdir('../')

    def createRepository(self):
        _exec('svnadmin create temp-svn-repo')
        _exec('svn checkout file:///%s %s' % (self.repoDir, self.workingDir))

    def destoryRepository(self):
        _exec('rm -fr %s %s' % (self.repoDir, self.workingDir))

    def commit(self):
        self._execsvn('svn commit -m "foo"')

    def addFile(self, name, content):
        file('%s/%s' % (self.workingDir, name), 'w').write(content)
        self._execsvn('svn add %s' % name)

def _exec(cmd):
    """Executes cmd and returns the lines of stdout."""
    stdin, stdout, stderr = os.popen3(cmd)

    outlines = stdout.readlines()
    errlines = stderr.readlines()

    stdin.close()
    stdout.close()
    stderr.close()

    if len(errlines) > 0:
        print 'Error executing: %s' % cmd
        print ''.join(errlines)
        print ''

    return outlines

"""Okay, run the test harness."""

# Clean out all of the old repositories and working directories
for old in filter(lambda x: x.startswith('temp-'), os.listdir('.')):
    _exec('rmdir /S /Q %s' % old)

harness = Harness()
# harness.addFacade(CvsFacade())
harness.addFacade(SvnFacade())

cases = map(lambda x: Case(x), filter(lambda x: x.endswith('.xml'), os.listdir('.')))

harness.run(cases)

