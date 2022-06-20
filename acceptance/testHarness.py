#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha2
# Copyright 2002, 2004 Stephen Haberman
#

"""
A harness to test each of the XML file workflows for each controller and each
view.
"""

import difflib
import getopt
import os
import re
import shutil
import stat
import sys
from xml.dom import minidom

sys.path.append('../')


class Expected:
    """
    Hold a line of expected output for comparison with actual output.
    The expected string may contain wildcards.
    """
    wildcard_re = re.compile(r'^(?P<pre>.*?)\#\#\#\#\#(?P<post>.*)$')

    def __init__(self, s):
        """
        Initialize object with expected string s.
        The expected string may contain the substring '#####', which can
        match any string of characters in the actual output (including the
        empty string).  '#####' may appear multiple times in the string.
        @param s: the expected string.
        """
        self.s = s
        restring = [r'^']
        while True:
            m = self.wildcard_re.match(s)
            if not m:
                break
            restring.append(re.escape(m.group('pre')))
            restring.append(r'.*')
            s = m.group('post')

        restring.append(re.escape(s))
        restring.append(r'$')
        restring = ''.join(restring)
        self.regexp = re.compile(restring)

    def matches(self, s):
        return bool(self.regexp.match(s))


class Harness:
    """
    A class to wrap the test context: creates a repository, executes the views,
    and compares the results.

    Given some L{Case}s, it uses the SCM controller facades to setup a context
    (e.g. creating a repository, changing a file), commit the change, gather
    the result, and compare the actual to what the L{Case} expected.
    """

    def __init__(self, facades, args):
        self.wait = 0
        self.facades = facades
        self.passes = 0
        self.failures = 0
        self.commits = None

        options, args = getopt.getopt(args, '', ['trace', 'trace-svn', 'do-not-destroy', 'commits='])
        for option, value in options:
            if option == '--trace':
                self.facades = [Tracer(x) for x in self.facades]
            if option == '--trace-svn':
                for facade in self.facades:
                    facade.tracesvn = 1
            if option == '--do-not-destroy':
                self.donotdestroy = 1
            if option == '--commits':
                self.commits = int(value)

        if len(args) == 0:
            # Create a L{Case} for each xml test file in this directory
            self.cases = [Case(x) for x in os.listdir('.') if x.endswith('.xml')]
        else:
            self.cases = [Case(x) for x in args]

    def run(self):
        """Runs a suite of L{Case}s."""
        for case in self.cases:
            print('Found case', case)
            self._runCase(case)
        print('')
        print('Passes: %s' % self.passes)
        print('Failures: %s' % self.failures)

    def _runCase(self, case):
        """Runs L{Case}."""

        for facade in self.facades:

            # We have some svn and cvs-only cases
            if facade.shouldSkipCase(case):
                print('Skipping facade', facade)
                continue

            print('Running facade', facade)

            # Each execution of the test case gets its own repository.
            facade.createRepository(case.config())

            for commit in case.commits()[:self.commits]:
                print('Running commit', commit)

                # Let the case do its stuff (e.g. modifying files)
                commit.doChanges(facade)

                # Tell the facade to commit, which will 'commit' and have the
                # controller execute the SCM system.
                facade.commit()

                # Check the results.
                for view in commit.views():
                    if not view.shouldBeExecuted(facade.name):
                        if facade.doesViewActualExist(view.name):
                            self.failures = self.failures + 1
                            print('Error, view %s was not supposed to execute' % view.name)
                        else:
                            self.passes = self.passes + 1
                        continue

                    expected = view.expected.strip().split('\n')
                    actual = [x.replace('\r', '') for x in facade.getViewActual(view.name).strip().split('\n')]

                    # Clean on the !svn/!cvs lines
                    expected = facade.cleanConditionals(expected)

                    if self._matchesIgnoringDates(expected, actual):
                        self.passes = self.passes + 1
                    else:
                        self.failures = self.failures + 1

                        delim = '=================================================='

                        print('Error, expected did not match actual:')
                        print('\n'.join(difflib.unified_diff(expected, actual)))
                        print(delim)

                        if self.wait == 1:
                            input('Waiting...')

                    facade.deleteActual(view.name)

            # We're done with this test case, so remove the repository.
            if not hasattr(self, 'donotdestroy'):
                facade.destroyRepository()

    def _matchesIgnoringDates(self, expected, actual):
        """
        Takes two lists of lines and sees if they are the same,
        ignoring parts of lines that are marked as being variable by
        having '#####' within them.
        """
        if len(expected) != len(actual):
            return 0

        for i in range(0, len(expected)):
            if not Expected(expected[i]).matches(actual[i]):
                return 0

        return 1

class Case:
    """A class to wrap the XML workflow files."""

    def __init__(self, fileName):
        """Init the test around an XML workflow file."""
        self.xmldoc = minidom.parse(file(fileName)).documentElement
        self.fileName = fileName

    def config(self):
        """Returns the configuration text for this case."""
        for config in self.xmldoc.getElementsByTagName("config"):
            for node in [x for x in config.childNodes if x.nodeType == x.TEXT_NODE]:
                return node.data
        return ''

    def commits(self):
        """Returns the commits that this case wants to do."""
        return [Commit(x) for x in self.xmldoc.getElementsByTagName("commit")]

    def __repr__(self):
        return '<Case %s>' % self.fileName

class Commit:
    """A class to wrap a series of changes to a working directory."""

    def __init__(self, commitElement):
        """Initializes the object from the XML element."""
        self.commitElement = commitElement

        # Store the message for the commit to self.message
        for e in self.commitElement.getElementsByTagName("message"):
            for node in e.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    self.message = node.data.strip()

    def doChanges(self, facade):
        """Loops through all of the changes for this commit."""
        for e in self.commitElement.childNodes:
            if e.nodeType == e.ELEMENT_NODE and e.tagName != 'view' and e.tagName != 'message':
                # The args to pass to the function
                args = {}

                # Each attribute is an argument, in order
                for key in list(e.attributes.keys()):
                    # Use str to that key is not unicode
                    args[str(key)] = e.attributes[key].value

                # The text is an argument too
                for node in e.childNodes:
                    if node.nodeType == node.TEXT_NODE:
                        text = node.data.strip()
                        # Ensure that non-empty files always end with a newline:
                        if text:
                            text += '\n'
                        args['content'] = text

                # Call the function
                getattr(facade, e.tagName)(**args)

        # Set the message for the commit
        facade.message = self.message

    def views(self):
        """Returns the views that are expected by this commit, viewName: results."""
        return [View(x) for x in self.commitElement.getElementsByTagName('view')]

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.message,)

class View:
    """A class that wraps the results of a view."""

    def __init__(self, viewElement):
        self.name = viewElement.attributes['name'].value
        self._executed = viewElement.attributes.get('executed')
        for node in viewElement.childNodes:
            if node.nodeType == node.TEXT_NODE:
                self.expected = node.data

    def shouldBeExecuted(self, facadeName):
        """@return: whether the 'executed' propery says the view should be done for none/svn/cvs"""
        if not self._executed:
            return True
        elif self._executed == 'none':
            return False
        elif self._executed == facadeName:
            return True
        else:
            return False

class ControllerFacade:
    """
    Wraps the interface to add/remove/changes files and directories in terms of
    each concrete repository.

    See L{SvnFacade} and L{CvsFacade} for implementations.
    """

    def __init__(self):
        self.mainPath = os.path.join(os.getcwd().replace('\\', '/'), '..', 'main.py')

    def getViewActual(self, viewName):
        """@return: the dumped results for the given view."""
        return file('%s/%s.txt' % (self.workingDir, viewName)).read()

    def deleteActual(self, viewName):
        """Clears out the old text file for the given view."""
        os.remove('%s/%s.txt' % (self.workingDir, viewName))

    def doesViewActualExist(self, viewName):
        """@return: whether the view has dumped to text"""
        return os.path.exists('%s/%s.txt' % (self.workingDir, viewName))

    def cleanConditionals(self, expected):
        """Removes the !svn/!cvs conditional lines from the expected output."""
        new = []

        goodStart = '!%s ' % self.name
        someStart = re.compile('^!((cvs)|(svn)) ')

        for line in expected:
            if line.startswith(goodStart):
                new.append(line[5:])
            elif someStart.match(line):
                # Ignore a line for a different facade
                pass
            else:
                new.append(line)

        return new

    def _readFile(self, name):
        f = file('%s/%s' % (self.workingDir, name), 'r')
        text = f.read()
        f.close()
        return text

    def _writeFile(self, name, text):
        f = file('%s/%s' % (self.workingDir, name), 'w')
        f.write(text)
        f.close()

    def _changeFile(self, name, fromLine, toLine, content):
        """Change a file in the working directory."""

        oldLines = self._readFile(name).splitlines(True)
        newLines = oldLines[:fromLine] + [content] + oldLines[toLine:]

        self._writeFile(name, ''.join(newLines))

    def shouldSkipCase(self, case):
        return False

class CvsFacade(ControllerFacade):
    """
    A facade for executing the test cases against a CVS installation (Unix only).
    """

    def __init__(self):
        ControllerFacade.__init__(self)

        self.repoDir = '%s/temp-cvs-repo' % os.getcwd().replace('\\', '/')
        self.workingDir = '%s/temp-cvs-wd' % os.getcwd().replace('\\', '/')
        self.message = ''
        self.name = 'cvs'
        self._initCvsVersion()

    def _initCvsVersion(self):
        """Determine CVS's version and store it in self._cvs_version.

        Parse the version and store it as a tuple in
        self._cvs_version.  Convert any dot-separated numeric prefix
        to a sequence of integers, and leave anything else as a single
        string.  For example, version '1.11.1p1' is stored as (1, 11,
        1, 'p1').  This scheme should make it easy to compare version
        numbers by comparing the tuples.

        The version is determined by running cvs -v and parsing
        stdout.  It is not known what range of CVS versions produce
        output compatible with the regular expression.  If the regular
        expression does not match, then _cvs_version is set to (0,),
        which looks older than any actual version.

        """

        output = _exec('cvs -vf')
        m = re.match(
            r'Concurrent Versions System \(CVS\) '
            r'(?P<numericpart>(\d+\.)+\d+)(?P<rest>\S*)'
            r' \(client\/server\)',
            output[1]
            )
        if m:
            v = [int(x) for x in m.group('numericpart').split('.')]
            if m.group('rest'):
                v.append(m.group('rest'))
            self._cvs_version = tuple(v)
        else:
            # If we can't parse the version output, we just assume it
            # was a very "old" version:
            self._cvs_version = (0,)

    def _execCvs(self, cmd):
        """Executes C{cmd} in the current directory with C{cvs -d :local:repoDir} as a prefix."""
        _exec('cvs -f -d :local:%s %s' % (self.repoDir, cmd))

    def _execInWorkingDir(self, cmd):
        """Executes C{cmd} in the working directory."""
        if hasattr(self, 'tracecvs'):
            print(cmd)
            input('')

        os.chdir(self.workingDir)
        _exec(cmd)
        os.chdir('../')

    def createRepository(self, config):
        _exec('mkdir temp-cvs-repo')
        self._execCvs('init')
        self._execCvs('checkout CVSROOT')

        # CVS's config file format strings changed, apparently at
        # version 1.12.x.  Therefore some of the configuration
        # settings are dependent on self._cvs_version.

        commitinfo = file('CVSROOT/commitinfo', 'w')
        if self._cvs_version >= (1, 12):
            commitinfo.write(
                'DEFAULT %s -c %s/CVSROOT/commitmessage.conf %%r/%%p %%s\n'
                % (self.mainPath, self.repoDir)
                )
        else:
            commitinfo.write(
                'DEFAULT %s -c %s/CVSROOT/commitmessage.conf\n'
                % (self.mainPath, self.repoDir)
                )
        commitinfo.close()

        loginfo = file('CVSROOT/loginfo', 'w')
        if self._cvs_version >= (1, 12):
            loginfo.write(
                'DEFAULT %s -c %s/CVSROOT/commitmessage.conf "%%p %%{s}" > commitmessage.out 2>&1\n'
                % (self.mainPath, self.repoDir)
                )
        else:
            loginfo.write(
                'DEFAULT %s -c %s/CVSROOT/commitmessage.conf %%{s} > commitmessage.out 2>&1\n'
                % (self.mainPath, self.repoDir)
                )
        loginfo.close()

        checkoutlist = file('CVSROOT/checkoutlist', 'w')
        checkoutlist.write('commitmessage.conf\n')
        checkoutlist.close()

        if self._cvs_version >= (1, 12):
            configfile = file('CVSROOT/config', 'a')
            configfile.write('UseNewInfoFmtStrings=yes\n')
            configfile.close()

        cvsConfig = config.replace('CONTROLLER', 'commitmessage.controllers.cvs.CvsController')
        cvsConfig = cvsConfig.replace('ACCEPTANCE_DIRECTORY', self.workingDir)

        newConfig = file('CVSROOT/commitmessage.conf', 'w')
        newConfig.write(cvsConfig)
        newConfig.close()

        os.chdir('CVSROOT')
        _exec('cvs -f add commitmessage.conf')
        _exec('cvs -f commit -m "Installing commitmessage."')
        os.chdir('..')

        _exec('mkdir temp-cvs-wd')
        os.chdir('temp-cvs-wd')
        self._execCvs('import -m "Importing." temp-cvs-wd vendor release')
        os.chdir('..')

        _exec('rm -fr temp-cvs-wd')
        self._execCvs('checkout temp-cvs-wd')

    def destroyRepository(self):
        _exec('rm -fr CVSROOT %s %s' % (self.repoDir, self.workingDir))

    def commit(self):
        self._writeFile('temp-message.txt', self.message)
        self._execInWorkingDir('cvs -f commit -F temp-message.txt')

    def addDirectory(self, name=''):
        os.mkdir('%s/%s' % (self.workingDir, name))
        self._execInWorkingDir('cvs -f add "%s"' % name)

    def addFile(self, name='', content=''):
        self._writeFile(name, content)
        self._execInWorkingDir('cvs -f add "%s"' % name)

    def addBinaryFile(self, name='', location=''):
        self._writeFile(name, self._readFile(location))
        self._execInWorkingDir('cvs -f add -kb "%s"' % name)

    def moveFile(self, fromPath='', toPath=''):
        self._execInWorkingDir('mv "%s" "%s"' % (fromPath, toPath))
        self._execInWorkingDir('cvs -f remove "%s"' % fromPath)
        self._execInWorkingDir('cvs -f add "%s"' % toPath)

    def removeFile(self, name=''):
        self._execInWorkingDir('rm "%s"' % name)
        self._execInWorkingDir('cvs -f remove "%s"' % name)

    def changeFile(self, name='', fromLine='', toLine='', content=''):
        self._changeFile(name, int(fromLine), int(toLine), content)

    def setProperty(self, name='', propery='', value=''):
        # CVS does not support file properties
        pass

    def shouldSkipCase(self, case):
        return case.fileName.startswith('svn')

class SvnFacade(ControllerFacade):
    """
    A facade for executing the test cases against SVN installation (both Unix and Windows).
    """

    def __init__(self):
        ControllerFacade.__init__(self)

        self.repoDir = '%s/temp-svn-repo' % os.getcwd().replace('\\', '/')
        self.workingDir = '%s/temp-svn-wd' % os.getcwd().replace('\\', '/')
        self.message = ''
        self.name = 'svn'

    def _execInWorkingDir(self, cmd):
        """Executes C{cmd} in the working directory."""
        # See if we should briefly pause.
        if hasattr(self, 'tracesvn'):
            print(cmd)
            input('')

        os.chdir(self.workingDir)
        _exec(cmd)
        os.chdir('../')

    def createRepository(self, config):
        _exec('svnadmin create temp-svn-repo')

        if os.sep == '/':
            newHook = file('%s/hooks/post-commit' % self.repoDir, 'w')
            arg = '$'
        else:
            newHook = file('%s/hooks/post-commit.bat' % self.repoDir, 'w')
            arg = '%'

        newHook.write('#!/bin/sh%s%spython %s -c "%s/commitmessage.conf" %s1 %s2 > commitmessage.out 2>&1' %
            (os.linesep, os.linesep, self.mainPath, self.repoDir, arg, arg))

        svnConfig = config.replace('CONTROLLER', 'commitmessage.controllers.svn.SvnController')
        svnConfig = svnConfig.replace('ACCEPTANCE_DIRECTORY', self.workingDir)

        newConfig = file('%s/commitmessage.conf' % self.repoDir, 'w')
        newConfig.write(svnConfig)
        newConfig.close()

        if os.sep == '/':
            os.chmod('%s/hooks/post-commit' % self.repoDir, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)

        _exec('svn checkout file:///%s %s' % (self.repoDir, self.workingDir))

    def destroyRepository(self):
        _exec('rm -fr %s %s' % (self.repoDir, self.workingDir))

    def commit(self):
        self._writeFile('temp-message.txt', self.message)
        self._execInWorkingDir('svn commit -F temp-message.txt')

    def addDirectory(self, name=''):
        os.mkdir('%s/%s' % (self.workingDir, name))
        self._execInWorkingDir('svn add "%s"' % name)

    def addFile(self, name='', content=''):
        self._writeFile(name, content)
        self._execInWorkingDir('svn add "%s"' % name)

    def addBinaryFile(self, name='', location=''):
        self._writeFile(name, self._readFile(location))
        self._execInWorkingDir('svn add "%s"' % name)

    def moveFile(self, fromPath='', toPath=''):
        self._execInWorkingDir('svn move "%s" "%s"' % (fromPath, toPath))

    def removeFile(self, name=''):
        self._execInWorkingDir('svn remove "%s"' % name)

    def changeFile(self, name='', fromLine='', toLine='', content=''):
        self._changeFile(name, int(fromLine), int(toLine), content)

    def setProperty(self, name='', property='', value=''):
        self._execInWorkingDir('svn propset "%s" "%s" "%s"' % (property, value, name))

    def shouldSkipCase(self, case):
        return case.fileName.startswith('cvs')

def _exec(cmd):
    """Executes C{cmd} and returns the lines of C{stdout}."""
    stdin, stdout, stderr = os.popen3(cmd)

    outlines = stdout.readlines()
    errlines = stderr.readlines()

    stdin.close()
    stdout.close()
    stderr.close()

    if len(errlines) > 0:
        for line in errlines:
            if not line.startswith('cvs'):
                print('Error executing: %s' % cmd)
                print(''.join(errlines))
                print('')
                break

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
        print('::%s' % name)
        input('')
        return getattr(self.wrapped, name)

    def __setattr__(self, name, value):
        setattr(self.wrapped, name, value)

def cleanup():
    """Removes lingering temp files from old tests."""
    if os.path.exists('commitmessage.out'):
        os.remove('commitmessage.out')
    for old in [x for x in os.listdir('.') if x.startswith('temp-') or x == 'CVSROOT']:
        shutil.rmtree(old)

if __name__ == '__main__':
    cleanup()

    # Create the harness for (currently, just) svn
    facades = [SvnFacade()]
    if os.name == 'posix':
        facades.append(CvsFacade())

    harness = Harness(facades, sys.argv[1:])
    harness.run()

