#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Bootstraps the commitmessage framework by reading in the configuration file
and initializing the controller."""

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
    if len(sys.argv) == 2:
        confFile = sys.argv[1]

    mainModulePath = os.path.abspath(os.path.dirname(sys.argv[0]))
    conf = CmConfigParser(mainModulePath + confFile)

    scm = conf.get('scm', 'interface')
    controller = getNewInstance(scm)

    controller.__init__(conf, sys.argv, sys.stdin)
    controller.process()
