#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
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
rootCmPath = currentDir

if __name__ == '__main__':
    sys.path.append(rootCmPath)

from commitmessage.exceptions import CmException
from commitmessage.util import CmConfigParser, getNewInstance

if __name__ == '__main__':
    configFile = 'commitmessage.conf'

    options, args = getopt.getopt(sys.argv[1:], "c:")
    for option, value in options:
        if option == "-c":
            configFile = value

    # Handle loading the default conf from within the commitmessage module
    if configFile[0] != '/' and configFile[0] != '.' and configFile[1] != ':':
       configFile = rootCmPath + os.sep + configFile

    config = CmConfigParser(os.path.realpath(configFile))

    scm = config.get('scm', 'interface')
    controller = getNewInstance(scm)

    # Remove the -c configFile argument that getopt looks for above and pass on
    # the rest of the arguments getopt did not grok to the controller
    cleanArgs = [sys.argv[0]]
    cleanArgs.extend(args)

    controller.__init__(config, cleanArgs, sys.stdin)

    # Get the other others in the 'scm' section
    for (name, value) in config.items('scm'):
        if name != 'interface':
            setattr(controller, name, value)

    controller.process()

