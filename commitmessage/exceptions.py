#!/usr/bin/env python
#
# commitmessage.py Version 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Central place for places to avoid import viscous circles."""

class CmException(Exception):
    """Root exception for commitmessage exceptions."""

    def __init__(self, value):
        """Initialize with a simple place holder value."""
        self.value = value

    def __str__(self):
        """Return the place holder value."""
        return self.value
