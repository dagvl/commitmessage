#!/usr/bin/env python

import glob
import logging
import os
import sys
import tarfile
import unittest
import zipfile

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
    modules = [_importAndReturnModule(module[:-3].replace(os.sep, '.')) for module in modules]
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
    version = '2.0-beta-5'
    subdir = 'commitmessage-%s/' % version

    if not os.path.exists('dist'):
        os.mkdir('dist')

    t = tarfile.TarFile('dist/commitmessage-%s.tar' % version, 'w')
    z = zipfile.ZipFile('dist/commitmessage-%s.zip' % version, 'w')

    for package in ['commitmessage', 'msnp']:
        for root, dirs, files in os.walk(package):
            if root.endswith('CVS'):
                continue

            if len(files) > 0:
                t.add(root, subdir + root, recursive=False)

            for file in files:
                if file.endswith('.py'):
                    file = root + os.sep + file
                    t.add(file, subdir + file)
                    z.write(file, subdir + file)

    for file in ['commitmessage.conf', 'INSTALL.txt', 'main.py', 'toc.py']:
        t.add(file, subdir + file)
        z.write(file, subdir + file)
    t.close()
    z.close()

