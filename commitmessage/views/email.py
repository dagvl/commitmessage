#!/usr/bin/env python
#
# commitmessage 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Provides several email Views for the commitmessage framework."""

import os
import sys
import time

if __name__ == '__main__':
    # Setup sys.path to correctly search for commitmessage.xxx[.yyy] modules
    currentDir = os.path.dirname(sys.argv[0])
    rootCmPath = os.path.abspath(currentDir + '/../../')
    sys.path.append(rootCmPath)

from StringIO import StringIO
from smtplib import SMTP
from commitmessage.framework import View

class BaseEmailView(View):
    """Provides a basic implementation of sending an email for other
    style-specific email Views to extend."""

    def execute(self):
        to = self.to().split(',')
        to = map(lambda t: t.strip(), to)

        text = StringIO('')
        text.write('To: %s\n' % ', '.join(to))
        text.write('From: %s\n' % self.keyword_from())
        text.write('Subject: %s\n' % self.subject())
        text.write('Date: %s -0000 (GMT)\n' % time.strftime('%A %d %B %Y %H:%M:%S', time.gmtime()))
        text.write('\n')

        if len(self.header()) > 0:
            text.write('%s\n\n' % self.header())
        self.generateBody(text)
        if len(self.footer()) > 0:
            text.write('\n\n%s' % self.footer())

        text.seek(0)
        body = text.read()

        smtp = SMTP(self.server())
        smtp.sendmail(self.keyword_from(), to, body)
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

    def printFiles(self, text, action):
        directories = self.model.directoriesWithFiles(action)
        if len(directories) > 0:
            text.write('%s%s\n' % (action[0].upper(), action[1:]))
            for dir in directories:
                text.write(' %s\n' % dir.path())
                files = dir.files(action)
                text.write('  %s' % files[0].name())
                for file in files[1:]:
                    text.write(', %s' % file.name())
                text.write('\n')
            text.write('\n')


    def generateBody(self, text):
        """Returns a string for the body of the email."""
        text.write('User: %s\n' % self.model.user())
        text.write('Date: %s\n' % time.strftime('%Y/%m/%d %I:%M %p'))
        text.write('\n')

        self.printFiles(text, 'added')
        self.printFiles(text, 'removed')
        self.printFiles(text, 'modified')

        text.write('Log\n %s\n\n' % self.model.log())

        text.write('File changes\n\n')
        for dir in self.model.directoriesWithFiles():
            s = 'Directory: %s' % dir.path()
            line = ''
            for i in range(0, len(s)):
                line = line + '='
            text.write('%s\n%s\n\n' % (s, line))

            for file in dir.files():
                text.write('File [%s]: %s\n' % (file.action(), file.name()))
                text.write('Delta lines: %s\n' % file.delta())
                text.write('%s\n' % file.diff())

class HtmlEmailView(BaseEmailView):
    """Sends out a HTML formatted email with the commit info in tables."""
    pass

