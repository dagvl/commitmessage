#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha2
# Copyright 2002, 2003 Stephen Haberman
#

"""A harness to test each of the XML file workflows for each controller and each view."""

import getopt
import os
import sys
from xml.dom import minidom

sys.path.append('../')

class ControllerFacade:
    """Wraps the interface to add/remove/changes files and directories in terms of each concrete repository."""

class Harness:
    """A class to wrap the test execution context; creates repository, executes the views, and compares the results."""

    def __init__(self, args):
        self.wait = 0
        self.facades = []
        self.passes = 0
        self.failures = 0

        options, args = getopt.getopt(args, 'w')
        for option, value in options:
            if option == '-w':
                self.wait = 1

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
            facade.createRepository(case.config())

            for commit in case.commits():
                """Let the case do its stuff."""
                commit.doChanges(facade)

                """Tell the facade to commit, which will 'commit' and have the controller executed by the SCM system."""
                facade.commit()

                """Check the results."""
                for view in commit.views():
                    if self.matchesIgnoringDates(view.expected, facade.actual(view.name)):
                        self.passes = self.passes + 1
                    else:
                        self.failures = self.failures + 1

                        delim = '=================================================='

                        print 'Error:'

                        print 'Expected:'
                        print delim
                        print view.expected
                        print delim

                        print 'Actual:'
                        print delim
                        print facade.actual(view.name)
                        print delim

                        if self.wait == 1:
                            raw_input('Waiting...')


            """We're done with this test case, so remove the repository."""
            facade.destoryRepository()

        print ''
        print 'Passes: %s' % self.passes
        print 'Failures: %s' % self.failures

    def matchesIgnoringDates(self, expected, actual):
        expected = expected.strip().split('\n')
        actual = actual.strip().split('\n')

        if len(expected) != len(actual):
            return 0

        for i in range(0, len(expected)):
            ignoredDateIndex = expected[i].find('#####')
            if ignoredDateIndex > -1:
                if expected[i][0:ignoredDateIndex] != actual[i][0:ignoredDateIndex]:
                    return 0
            elif expected[i] != actual[i]:
                return 0

        return 1

class Case:
    """A class to wrap the XML workflow files."""

    def __init__(self, fileName):
        """Init the test around an XML workflow file."""
        self.xmldoc = minidom.parse(file(fileName)).documentElement

    def config(self):
        """Returns the configuration text for this case."""
        for config in self.xmldoc.getElementsByTagName("config"):
            for node in filter(lambda x: x.nodeType == x.TEXT_NODE, config.childNodes):
                return node.data
        return ''

    def commits(self):
        """Returns the commits that this case wants to do."""
        return map(lambda x: Commit(x), self.xmldoc.getElementsByTagName("commit"))

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

                # The text is an argument too
                for node in e.childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        args.append(node.data)

                # Call the function
                getattr(facade, e.tagName)(*args)

    def views(self):
        """Returns the views that are expected by this commit, viewName: results."""
        return map(lambda x: View(x), self.commitElement.getElementsByTagName('view'))

class View:
    """A class that wraps the results of a view."""

    def __init__(self, viewElement):
        self.name = viewElement.attributes['name'].value
        for node in viewElement.childNodes:
            if node.nodeType == node.TEXT_NODE:
                self.expected = node.data

class CvsFacade:

    def createRepository(self):
        pass

class SvnFacade:

    def __init__(self):
        self.repoDir = '%s/temp-svn-repo' % os.getcwd().replace('\\', '/')
        self.workingDir = '%s/temp-svn-wd' % os.getcwd().replace('\\', '/')
        self.log = ''

    def _execsvn(self, cmd):
        """Executes cmd in the working directory."""
        os.chdir(self.workingDir)
        _exec(cmd)
        os.chdir('../')

    def createRepository(self, config):
        _exec('svnadmin create temp-svn-repo')

        newHook = file('%s/hooks/post-commit.bat' % self.repoDir, 'w')
        newHook.write('..\\..\\commitmessage\\main.py -c "%s/commitmessage.conf" %%1 %%2 > commitmessage.out 2>&1' % self.repoDir)

        newConfig = file('%s/commitmessage.conf' % self.repoDir, 'w')
        newConfig.write(config)

        _exec('svn checkout file:///%s %s' % (self.repoDir, self.workingDir))

    def destoryRepository(self):
        _exec('rm -fr %s %s' % (self.repoDir, self.workingDir))

    def actual(self, viewName):
        """Returns the dumped results for the given view."""
        return file('%s/%s.txt' % (self.workingDir, viewName)).read()

    def commit(self):
        self._execsvn('svn commit -m "%s"' % self.log)

    def addFile(self, name, content):
        file('%s/%s' % (self.workingDir, name), 'w').write(content.strip())
        self._execsvn('svn add %s' % name)

    def message(self, log):
        self.log = log.strip()

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

harness = Harness(sys.argv[1:])
# harness.addFacade(CvsFacade())
harness.addFacade(SvnFacade())

cases = map(lambda x: Case(x), filter(lambda x: x.endswith('.xml'), os.listdir('.')))

harness.run(cases)

