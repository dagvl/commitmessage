#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""Basic utility functions and classes (L{CmConfigParser}, L{getNewInstance}, and L{execute})"""

from ConfigParser import ConfigParser
from types import ModuleType
import new
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

    def getModulesForPath(self, commitPath):
        """@return: the modules that match the given path (and should hence have their views executed)"""
        modules = []
        for module in ConfigParser.options(self, 'modules'):
            match = ConfigParser.get(self, 'modules', module)
            p = re.compile(match)
            if p.search(commitPath):
                modules.append(module)
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
        viewNames = p.split(viewLine)

        views = []
        for viewName in viewNames:
            fullClassName = ConfigParser.get(self, 'views', viewName)
            view = getNewInstance(fullClassName)
            view.__init__(viewName, model)

            # Setup default values
            if ConfigParser.has_section(self, viewName):
                for name in ConfigParser.options(self, viewName):
                    value = ConfigParser.get(self, viewName, name, 1)
                    view.__dict__[name] = str(Itpl(value))

            # Setup module-specific values
            forViewPrefix = re.compile('^%s.' % viewName)
            for option in ConfigParser.options(self, module):
                if forViewPrefix.search(option):
                    # Take off the 'viewName.'
                    name = option[len(viewName)+1:]
                    value = ConfigParser.get(self, module, option, 1)
                    view.__dict__[name] = str(Itpl(value))

            views.append(view)
        return views

def getNewInstance(fullClassName, searchPath=['./']):
    """@return: an instance of the fullClassName class WITHOUT the C{__init__} method having been called"""

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
    """@return: the contents of C{stdout} as a list of lines after executing C{command}"""
    pipeIn, pipeOut = os.popen2(command)
    lines = pipeOut.readlines()
    pipeIn.close()
    pipeOut.close()
    return lines

def _doctest():
    import doctest, util
    return doctest.testmod(util)

if __name__ == "__main__":
    _doctest()

