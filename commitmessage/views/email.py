#!/usr/bin/env python
#
# commitmessage 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Provides several email Views for the commitmessage framework."""

import os
import sys

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from smtplib import SMTP
from commitmessage.framework import View

class BaseEmailView(View):
    """Provides a basic implementation of sending an email for other
    style-specific email Views to extend."""

    def execute(self):
        text = '%s\n%s\n%s' % (header(), self.generateBody(), footer())
        smtp = SMTP(self.server())
        smtp.sendmail(self.keyword_from(), self.to(), text)
        smtp.quit()

    def footer(self, footer=None):
        """A string of text to include at the beginning of the body."""
        if footer != None: self._footer = footer
        return self._footer

    def header(self, header=None):
        """A string of text to include at the beginning of the body."""
        if header != None: self._header = header
        return self._header

    def keyword_from(self, afrom=None):
        """Who the email is coming from, e.g. 'cvs-commits@test.com'.

        The config file uses 'from', but in Python, 'from' is a keyword, so the
        class cannot use it as a method name, so 'keyword_from' is a hack around
        it."""
        return self._from

    def server(self, server=None):
        """The mail server to connect to when sending the email."""
        if server != None: self._server = server
        return self._server

    def subject(self, subject=None):
        """The subject for the email."""
        if subject != None: self._subject = subject
        return self._subject

    def to(self, to=None):
        """Who to send the email to; a comma-separated list of email addresses,
        e.g. 'foo@bar.com, test@test.com'."""
        if to != None: self._to = to
        return self._to

class ApacheStyleEmailView(BaseEmailView):
    """Sends out an email formatted in a style mimicking Apace commit emails."""
    pass

class TigrisStyleEmailView(BaseEmailView):
    """Sends out an email formatted in a style mimicking Tigris commit emails."""
    pass

class HtmlEmailView(BaseEmailView):
    """Sends out a HTML formatted email with the commit info in tables."""
    pass

