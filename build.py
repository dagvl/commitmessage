#!/usr/bin/env python

import glob
import logging
import os
import sys
import unittest

sys.path.extend(['./src', './test'])

handler = logging.FileHandler('pyow.log', 'w')
format = logging.Formatter(logging.BASIC_FORMAT)
handler.setFormatter(format)
logging.getLogger('pyow').addHandler(handler)
logging.getLogger('pyow').setLevel(logging.DEBUG)

# Save for the _unittest method
oldargv = sys.argv

def _unittest():
    """
    Passed to the C{unittest} module; returns to it one test suite with all of
    the unit tests in the C{tests} directory.
    """
    modules = []
    for root, dirs, files in os.walk('test'):
        for file in files:
            if file.endswith('est.py'):
                modules.append('%s%s%s' % (root, os.sep, file))
    modules = [_importAndReturnModule(module[5:-3].replace(os.sep, '.')) for module in modules]
    tests = [unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules]
    return unittest.TestSuite(tests)

def _importAndReturnModule(name):
    """
    C{__import__} returns the top-level package (e.g. C{package} in
    C{__import__(package.name))}; this returns C{name} instead. Gotten from the
    Python documentation.
    """
    module = __import__(name)
    parts = name.split('.')
    for part in parts[1:]:
        module = getattr(module, part)
    return module

if sys.argv[1] == 'unittest':
    sys.argv = sys.argv[0:1]
    unittest.main(defaultTest='_unittest')

if sys.argv[1] == 'clean':
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                remove = '%s%s%s' % (root, os.sep, file)
                print 'Removing %s ' % remove
                os.unlink(remove)

if sys.argv[1] == 'doctest':
    modules = []
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.py'):
                modules.append('%s%s%s' % (root, os.sep, file))
    modules = [_importAndReturnModule(module[4:-3].replace(os.sep, '.')) for module in modules]
    for module in modules:
        if hasattr(module, '_doctest'):
            module._doctest()

if sys.argv[1] == 'docs':
    from epydoc.cli import cli
    sys.argv = ['', 'src/decorator.py', 'src/doctags.py', 'src/smt', 'src/pyow']
    cli()

if sys.argv[1] == 'tags':
    import os
    os.popen('exctags -R src')

