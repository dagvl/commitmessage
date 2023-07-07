#!/usr/bin/python3
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
    profiling = 0
    # Handle loading the default conf from within the commitmessage module
    defaultConfigFile = rootCmPath + os.sep + 'commitmessage.conf'
    configFile = defaultConfigFile

    options, args = getopt.getopt(sys.argv[1:], "hc:p")
    for option, value in options:
        if option == '-c':
            configFile = value
        if option == '-p':
            profiling = 1
        if option == '-h':
            print(
f'''Commit message sender
Args:
-c <configfile>: read from config file, default: {defaultConfigFile}
-p: enable profiling
'''
)
            sys.exit(1)

    if profiling:
        import cProfile
        i = 0
        while 1:
            f = currentDir + os.sep + 'commitmessage%s.profile' % i
            if not os.path.exists(f): break
            i += 1
        profile = cProfile.Profile()
        profile.enable()

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
        profile.disable()
        profile.create_stats()
        profile.dump_stats(f)

if __name__ == '__main__':
    main()

