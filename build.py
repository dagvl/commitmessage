#!/usr/bin/env python

import glob
import logging
import os
import sys
import tarfile
import unittest

sys.path.extend(['./src', './test'])

# Save for the _unittest method
oldargv = sys.argv

# def _unittest():
#     """
#     Passed to the C{unittest} module; returns to it one test suite with all of
#     the unit tests in the C{tests} directory.
#     """
#     modules = []
#     for root, dirs, files in os.walk('test'):
#         for file in files:
#             if file.endswith('est.py'):
#                 modules.append('%s%s%s' % (root, os.sep, file))
#     modules = [_importAndReturnModule(module[5:-3].replace(os.sep, '.')) for module in modules]
#     tests = [unittest.defaultTestLoader.loadTestsFromModule(module) for module in modules]
#     return unittest.TestSuite(tests)
#
# if sys.argv[1] == 'unittest':
#     sys.argv = sys.argv[0:1]
#     unittest.main(defaultTest='_unittest')

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

if sys.argv[1] == 'clean':
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                remove = '%s%s%s' % (root, os.sep, file)
                print 'Removing %s ' % remove
                os.unlink(remove)

if sys.argv[1] == 'doctest':
    modules = []
    for root, dirs, files in os.walk('commitmessage'):
        for file in files:
            if file.endswith('.py'):
                modules.append('%s%s%s' % (root, os.sep, file))
    modules = [_importAndReturnModule(module[4:-3].replace(os.sep, '.')) for module in modules]
    for module in modules:
        if hasattr(module, '_doctest'):
            module._doctest()

if sys.argv[1] == 'docs':
    from epydoc.cli import cli
    sys.argv = ['', '-o', 'www/docs', 'commitmessage']
    cli()

if sys.argv[1] == 'tags':
    import os
    os.popen('exctags -R commitmessage')

if sys.argv[1] == 'dist':
    t = tarfile.TarFile('commitmessage.tar', 'w')
    for root, dirs, files in os.walk('commitmessage'):
        dirAdded = False
        for file in files:
            if file.endswith('.py'):
                # See if we need to add the directory
                if not dirAdded:
                    t.add('%s' % root, recursive=False)
                    dirAdded = True
                t.add('%s%s%s' % (root, os.sep, file))
    t.add('commitmessage.conf')
    t.close()

