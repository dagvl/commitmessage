#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""Basic utility functions and classes (L{CmConfigParser}, L{getNewInstance}, and L{execute})"""

from configparser import ConfigParser
from subprocess import Popen, PIPE
import types
import os
import re
import sys

from commitmessage.Itpl import Itpl
from commitmessage.exceptions import CmException

class CmConfigParser(ConfigParser):
    """Provides config-centric logic for views and modules that would be confused elsewhere"""

    def __init__(self, filePath):
        """Initializes with the configuration file at C{filePath}"""
        ConfigParser.__init__(self)
        ConfigParser.readfp(self, open(filePath))

        self.userMap = {}
        if self.has_section('userMap'):
            for name in self.options('userMap'):
                self.userMap[name] = self.get('userMap', name)

    def getSummaryThreshold(self):
        """@return: the summary breakout threshold in KB. If the diffs exceed this size, the controller should null the individual file diffs"""
        threshold = -1

        if self.has_option('scm', 'summaryThreshold'):
            #Convert the conf value from KB to bytes
            threshold = int(self.getint('scm', 'summaryThreshold') * 1024)

        return threshold

    def getModulesForPath(self, commitPath):
        """@return: the modules that match the given path (and should hence have their views executed)"""
        modules = []

        # Load the user-defined modules
        for module in ConfigParser.options(self, 'modules'):
            p = re.compile(ConfigParser.get(self, 'modules', module))
            if p.match(commitPath):
                modules.append(module)

        # Add default if necessary
        if len(modules) == 0:
            modules.append('DEFAULT_MODULE')

        # Always add universal unless the user has already put it there
        if 'UNIVERSAL_MODULE' not in modules:
            modules.append('UNIVERSAL_MODULE')

        # Only return verified modules that have their own section
        modules = [m for m in modules if ConfigParser.has_section(self, m)]

        modules.sort()
        return modules

    def getViewsForModule(self, module, model):
        """
        @param module: the name of the model to get the views for
        @param model: the L{commitmessage.model.Model} to initialize views with
        @return: the configured views for a module
        """
        viewLine = ConfigParser.get(self, module, 'views')
        p = re.compile(',\s?')
        viewNames = [name.strip() for name in p.split(viewLine) if len(name.strip()) > 0]

        userMap = self.userMap

        views = []
        for viewName in viewNames:
            fullClassName = ConfigParser.get(self, 'views', viewName)
            view = getNewInstance(fullClassName)
            view.__init__(viewName, model)

            # Setup default values
            if ConfigParser.has_section(self, viewName):
                for name in ConfigParser.options(self, viewName):
                    value = ConfigParser.get(self, viewName, name, raw=1)
                    view.__dict__[name] = str(Itpl(value))

            # Setup module-specific values
            forViewPrefix = re.compile('^%s.' % viewName)
            for option in ConfigParser.options(self, module):
                if forViewPrefix.search(option):
                    # Take off the 'viewName.'
                    name = option[len(viewName)+1:]
                    value = ConfigParser.get(self, module, option, raw=1)
                    view.__dict__[name] = str(Itpl(value))

            views.append(view)
        return views

    """Patch by Juan F. Codagnone <juam@users.sourceforge.net> for Python 2.2.1 support."""
    if sys.hexversion < 0x2030000:
        def items(self, section):
            """ there is an items() method since python 2.3.  """
            ret = []
            keys = self.options(section)
            for i in keys:
                ret.append( (i,self.get(section, i)) ) 

            return ret

def getNewInstance(fullClassName, searchPath=['./']):
    """@return: an instance of the fullClassName class WITHOUT the C{__init__} method having been called"""

    # Was original, then modified with parts of
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/223972

    parts = fullClassName.split('.')
    className = parts.pop()
    moduleName = parts.pop()
    package = '.'.join(parts)

    try:
        module = sys.modules[package + '.' + moduleName]
    except KeyError:
        if len(parts) > 0:
            module = __import__(package + "." + moduleName, globals(), locals(), [''])
        else:
            module = __import__(moduleName, globals(), locals())

    function = getattr(module, className)

    if not callable(function):
        raise ImportError(fullFuncError)

    return function.__new__(function)

def execute(command):
    """@return: the contents of C{stdout} as a list of lines after executing C{command}"""
    p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE,
              close_fds=True)
    (pipeIn, pipeOut, pipeErr) = (p.stdin, p.stdout, p.stderr)
    lines = [x.decode('utf-8') for x in pipeOut.readlines()]
    errors = [x.decode('utf-8') for x in pipeErr.readlines()]
    err = '\n'.join(errors)
    pipeIn.close(), pipeOut.close(), pipeErr.close()

    # If no lines are there, an error might have occurred
    if len(lines) == 0:

        # See if it is permission related (e.g. creating .svnlook)
        if err.find('Permission denied') != -1:
            os.chdir('/tmp')

            # Retry
            p = Popen(command, shell=True, stdin=PIPE, stdout=PIPE,
                      stderr=PIPE, close_fds=True)
            (pipeIn, pipeOut, pipeErr) = (p.stdin, p.stdout, p.stderr)
            lines = [x.decode('utf-8') for x in pipeOut.readlines()]
            errors = [x.decode('utf-8') for x in pipeErr.readlines()]
            err = '\n'.join(errors)
            pipeIn.close(), pipeOut.close(), pipeErr.close()

        # If there is still an error, print it
        if len(err) > 0:
            print(err)

    return lines

def _doctest():
    import doctest, util
    return doctest.testmod(util)

if __name__ == "__main__":
    _doctest()

