#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha2
# Copyright 2002, 2003 Stephen Haberman
#

"""A harness to test each of the XML file workflows for each controller and each view."""

import difflib
import getopt
import os
import sys
from xml.dom import minidom

sys.path.append('../')

class ControllerFacade:
    """Wraps the interface to add/remove/changes files and directories in terms of each concrete repository."""

class Harness:
    """A class to wrap the test execution context; creates repository, executes the views, and compares the results."""

    def __init__(self, facades, args):
        self.wait = 0
        self.facades = facades
        self.passes = 0
        self.failures = 0

        options, args = getopt.getopt(args, '', ['trace', 'trace-svn'])
        for option, value in options:
            if option == '--trace':
                self.facades = [Tracer(x) for x in self.facades]
            if option == '--trace-svn':
                for facade in self.facades:
                    facade.tracesvn = 1

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
                    expected = view.expected.strip().split('\n')
                    actual = [x.replace('\r', '') for x in facade.actual(view.name).strip().split('\n')]

                    if self.matchesIgnoringDates(expected, actual):
                        self.passes = self.passes + 1
                    else:
                        self.failures = self.failures + 1

                        delim = '=================================================='

                        print 'Error, expected did not match actual:'
                        print '\n'.join(difflib.unified_diff(expected, actual))
                        print delim

                        if self.wait == 1:
                            raw_input('Waiting...')


            """We're done with this test case, so remove the repository."""
            facade.destroyRepository()

        print ''
        print 'Passes: %s' % self.passes
        print 'Failures: %s' % self.failures

    def matchesIgnoringDates(self, expected, actual):
        """Takes two lists of lines."""
        if len(expected) != len(actual):
            return 0

        for i in range(0, len(expected)):
            ignoredDateIndex = expected[i].find('#####')
            if ignoredDateIndex > -1:
                if expected[i][0:ignoredDateIndex] != actual[i][0:ignoredDateIndex]:
                    print expected[i-1:i+2]
                    print actual[i-1:i+2]
                    return 0
            elif expected[i] != actual[i]:
                print expected[i-1:i+2]
                print actual[i-1:i+2]
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
            for node in [x for x in config.childNodes if x.nodeType == x.TEXT_NODE]:
                return node.data
        return ''

    def commits(self):
        """Returns the commits that this case wants to do."""
        return [Commit(x) for x in self.xmldoc.getElementsByTagName("commit")]

class Commit:
    """A class to wrap a series of changes to a working directory."""

    def __init__(self, commitElement):
        """Initializes the object from the XML element."""
        self.commitElement = commitElement

    def doChanges(self, facade):
        """Loops through all of the changes for this commit."""
        for e in self.commitElement.childNodes:
            if e.nodeType == e.ELEMENT_NODE and e.tagName != 'view' and e.tagName != 'message':
                # The args to pass to the function
                args = {}

                # Each attribute is an argument, in order
                for key in e.attributes.keys():
                    # Use str to that key is not unicode
                    args[str(key)] = e.attributes[key].value

                # The text is an argument too
                for node in e.childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        args['content'] = node.data.strip()

                # Call the function
                getattr(facade, e.tagName)(**args)
        # Set the message for the commit
        for e in self.commitElement.getElementsByTagName("message"):
            for node in e.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    facade.message = node.data.strip()

    def views(self):
        """Returns the views that are expected by this commit, viewName: results."""
        return [View(x) for x in self.commitElement.getElementsByTagName('view')]

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
        self.message = ''

    def _execsvn(self, cmd):
        """Executes cmd in the working directory."""
        # See if we should briefly pause.
        if hasattr(self, 'tracesvn'):
            print cmd
            raw_input('')

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

    def destroyRepository(self):
        _exec('rm -fr %s %s' % (self.repoDir, self.workingDir))

    def actual(self, viewName):
        """Returns the dumped results for the given view."""
        return file('%s/%s.txt' % (self.workingDir, viewName)).read()

    def commit(self):
        self._openFile('temp-message.txt', 'w').write(self.message)
        self._execsvn('svn commit -F temp-message.txt')

    def _openFile(self, name, flags):
        return file('%s/%s' % (self.workingDir, name), flags)

    def addDirectory(self, name=''):
        os.mkdir('%s/%s' % (self.workingDir, name))
        self._execsvn('svn add %s' % name)

    def addFile(self, name='', content=''):
        self._openFile(name, 'w').write(content)
        self._execsvn('svn add %s' % name)

    def addReferencedFile(self, name='', location=''):
        self._openFile(name, 'w').writelines(self._openFile(location, 'r').readlines())
        self._execsvn('svn add %s' % name)

    def moveFile(self, fromPath='', toPath=''):
        self._execsvn('svn move %s %s' % (fromPath, toPath))

    def removeFile(self, name=''):
        self._execsvn('svn remove %s' % name)

    def changeFile(self, name='', fromLine='', toLine='', content=''):
        fromLine = int(fromLine)
        toLine = int(toLine)

        oldLines = self._openFile(name, 'r').readlines()
        newLines = []

        for i in range(0, fromLine):
            newLines.append(oldLines[i])

        newLines.extend(content.split('\n'))

        for i in range(fromLine, toLine):
            newLines.append(oldLines[i])

        self._openFile(name, 'w').write('\n'.join(newLines))

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

class Tracer:
    """Lets the user walk step-by-step through a test to watch the changes on the file system."""

    def __init__(self, wrapped):
        """wrapped is the instance to interrupt calls to any attribute."""
        # Use __dict__ to bypass our __setattr__ below.
        self.__dict__['wrapped'] = wrapped

    def __getattr__(self, name):
        """Prints out name of the attribute being asked, waits for user
        feedback, and then returns the attribute from the wrapped object."""
        print '::%s' % name
        raw_input('')
        return getattr(self.wrapped, name)

    def __setattr__(self, name, value):
        setattr(self.wrapped, name, value)

"""Okay, run the test harness."""

# Clean out all of the old repositories and working directories
for old in filter(lambda x: x.startswith('temp-'), os.listdir('.')):
    _exec('rmdir /S /Q %s' % old)

harness = Harness([SvnFacade()], sys.argv[1:])

cases = [Case(x) for x in os.listdir('.') if x.endswith('.xml')]

harness.run(cases)
