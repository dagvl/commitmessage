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
        text.write('To: %s\r\n' % ', '.join(to))
        text.write('From: %s\r\n' % self.keyword_from())
        text.write('Subject: %s\r\n' % self.subject())
        text.write('Date: %s -0000 (GMT)\r\n' % time.strftime('%A %d %B %Y %H:%M:%S', time.gmtime()))
        text.write('\r\n\r\n')

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

    def generateBody(self, text):
        """Returns a string for the body of the email."""
        text.write('User: %s\n' % self.model.user())
        text.write('Date: %s\n' % time.strftime('%Y/%m/%d %I:%M %p'))
        text.write('\n')

        addFileDirs = self.model.directoriesWithFiles('added')
        if len(addFileDirs) > 0:
            text.write('Added\n')
            for dir in addFileDirs:
                text.write(' %s\n' % dir.path())
                files = dir.files('added')
                text.write('  %s' % files[0].name())
                for file in files[1:]:
                    text.write(', %s' % file.name())
                text.write('\n')
            text.write('\n')

        remFileDirs = self.model.directoriesWithFiles('removed')
        if len(remFileDirs) > 0:
            text.write('Removed\n')
            for dir in remFileDirs:
                text.write(' %s\n' % dir.path())
                files = dir.files('removed')
                text.write('  %s' % files[0].name())
                for file in files[1:]:
                    text.write(', %s' % file.name())
                text.write('\n')
            text.write('\n')

        modFileDirs = self.model.directoriesWithFiles('modified')
        if len(modFileDirs) > 0:
            text.write('Modified\n')
            for dir in modFileDirs:
                text.write(' %s\n' % dir.path())
                files = dir.files('modified')
                text.write('  %s' % files[0].name())
                for file in files[1:]:
                    text.write(', %s' % file.name())
                text.write('\n')
            text.write('\n')

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

