#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""
Contains the L{CmException} class
"""

class CmException(Exception):
    """The exception for all commitmessage-related exceptions"""

    def __init__(self, value):
        """@param value: a simple value"""
        self.value = value

    def __str__(self):
        """@return: the value passed to the constructor"""
        return self.value

