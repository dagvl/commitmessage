#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""Bootstraps the commitmessage framework

It does so by setting up the C{sys.path} (it assumes this file, C{main.py}, is
in the C{commitmessage} package), reading in the configuration file, and
initializing the controller.
"""

import getopt
import os
import sys

# Assume this main.py is in the parent directory of the commitmessage package
# and setup sys.path to import the rest of the commitmessage package

currentDir = os.path.dirname(sys.argv[0])
rootCmPath = os.path.realpath(currentDir)

if __name__ == '__main__':
    sys.path.append(rootCmPath)

from commitmessage.exceptions import CmException
from commitmessage.util import CmConfigParser, getNewInstance

def main():
    profiling, configFile = 0, 'commitmessage.conf'

    options, args = getopt.getopt(sys.argv[1:], "c:p")
    for option, value in options:
        if option == '-c':
            configFile = value
        if option == '-p':
            profiling = 1

    if profiling:
        import hotshot
        i = 0
        while 1:
            f = currentDir + os.sep + 'commitmessage%s.profile' % i
            if not os.path.exists(f): break
            i += 1
        profile = hotshot.Profile(f)
        profile.start()

    # Handle loading the default conf from within the commitmessage module
    if configFile[0] != '/' and configFile[0] != '.' and configFile[1] != ':':
       configFile = rootCmPath + os.sep + configFile

    config = CmConfigParser(configFile)

    controller = getNewInstance(config.get('scm', 'controller'))

    # Remove the -c configFile argument that getopt looks for above and pass on
    # the rest of the arguments getopt did not grok to the controller
    cleanArgs = [sys.argv[0]]
    cleanArgs.extend(args)

    # getNewInstance does not call the __init__ constructor, so we do
    controller.__init__(config, cleanArgs, sys.stdin)

    controller.process()

    if profiling:
        profile.stop()
        profile.close()

if __name__ == '__main__':
    main()

