#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Bootstraps the commitmessage framework by reading in the configuration file
and initializing the controller."""

import getopt
import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../')
    sys.path.append(rootCmPath)

from commitmessage.exceptions import CmException
from commitmessage.util import CmConfigParser, getNewInstance

if __name__ == '__main__':
    confFile = '/commitmessage.conf'

    options, args = getopt.getopt(sys.argv[1:], "c:")
    for option, value in options:
        if option == "-c":
            confFile = value

    mainModulePath = os.path.abspath(os.path.dirname(sys.argv[0]))
    conf = CmConfigParser(mainModulePath + confFile)

    scm = conf.get('scm', 'interface')
    controller = getNewInstance(scm)

    cleanArgs = [sys.argv[0]]
    cleanArgs.extend(args)
    controller.__init__(conf, cleanArgs, sys.stdin)
    controller.process()
