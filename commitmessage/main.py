#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""
Bootstraps the commitmessage framework by reading in the configuration file
and initializing the controller.
"""

import getopt
import os
import sys

# Assume this main.py is in the commitmessage package and setup sys.path to
# import the rest of the commitmessage package
currentDir = os.path.dirname(sys.argv[0])
rootCmPath = os.path.abspath(currentDir + '/../')

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

    # Handle relative paths.
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
    controller.process()

