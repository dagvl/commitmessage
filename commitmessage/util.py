#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002, 2003 Stephen Haberman
#

"""Provides some basic utility classes, such as wrapping the ConfigParser to add
commitmessage-specific logic to the view/module lookups."""

from ConfigParser import ConfigParser
from types import ModuleType
import imp
import new
import os
import re
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    sys.path.append(rootCmPath)

from commitmessage.Itpl import Itpl
from commitmessage.exceptions import CmException

class CmConfigParser(ConfigParser):
    """Provides cm-specific logic, such as getting view settings from both the
    view definition and the module-specific settings."""

    def __init__(self, filePath):
        """Initializes the CmConfigParser against the given conf file."""
        ConfigParser.__init__(self)
        ConfigParser.readfp(self, open(filePath))

    def getModulesForPath(self, commitPath):
        """Returns the modules that match the given path."""
        modules = []
        for module in ConfigParser.options(self, 'modules'):
            match = ConfigParser.get(self, 'modules', module)
            p = re.compile(match)
            if p.search(commitPath):
                modules.append(module)
        modules.sort()
        return modules

    def getViewsForModule(self, module, model):
        viewLine = ConfigParser.get(self, module, 'views')
        p = re.compile(',\s?')
        viewNames = p.split(viewLine)

        views = []
        for name in viewNames:
            fullClassName = ConfigParser.get(self, 'views', name)
            view = getNewInstance(fullClassName)
            print view
            view.__init__(name, model)
            # Setup default values
            for option in ConfigParser.options(self, name):
                value = ConfigParser.get(self, name, option, 1)
                view.__dict__['_%s' % option] = str(Itpl(value))
            # Setup module-specific values
            forViewPrefix = re.compile('^%s.' % name)
            for option in ConfigParser.options(self, module):
                if forViewPrefix.search(option):
                    # Take off the 'name.'
                    realName = option[len(name)+1:]
                    value = ConfigParser.get(self, module, option, 1)
                    view.__dict__['_%s' % realName] = str(Itpl(value))
            views.append(view)
        return views

def getNewInstance(fullClassName, searchPath=['./']):
    """Returns an instance of the fullClassName class WITHOUT the __init__ method having been called."""

    # Was original, then modified with parts of
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/223972

    parts = fullClassName.split('.')
    functionName = parts.pop()
    moduleName = parts.pop()
    path = '.'.join(parts)

    try:
        module = sys.modules[moduleName]
    except KeyError:
        if len(parts) > 0:
            module = __import__(path + "." + moduleName, globals(), locals(), [''])
        else:
            module = __import__(moduleName, globals(), locals())

    function = getattr(module, functionName)

    if not callable(function):
        raise ImportError(fullFuncError)

    return new.instance(function)

def execute(command):
    """Executes a command line and returns the contents of stdout as a list of liens."""
    pipeIn, pipeOut = os.popen2(command)
    lines = pipeOut.readlines()
    pipeIn.close()
    pipeOut.close()
    return lines

def _test():
    """Executes doctest on this module."""
    import doctest, util
    return doctest.testmod(util)

if __name__ == "__main__":
    _test()
