#!/usr/bin/env python
#
# commitmessage 2.0-alpha1
# Copyright 2002 Stephen Haberman
#

"""Provides several email Views for the commitmessage framework."""

import os
import sys
import time

from StringIO import StringIO
from smtplib import SMTP
from commitmessage.framework import View

class BaseEmailView(View):
    """Provides a basic implementation of sending an email for other style-specific email views to extend."""

    def __init__(self, name, model):
        """Initialize all the username to None."""
        View.__init__(self, name, model)

        self.acceptance = 0
        self.username = None
        self.header = 0
        self.footer = 0

    def __getitem__(self, name):
        """Used to get the 'from' attribute."""
        return self.__dict__[name]

    def execute(self):
        text = StringIO('')
        text.write('To: %s\n' % self.to)
        text.write('From: %s\n' % self['from'])
        text.write('Subject: %s\n' % self.subject)
        text.write('Date: %s -0000 (GMT)\n' % time.strftime('%A %d %B %Y %H:%M:%S', time.gmtime()))
        text.write('\n')

        if len(self.header) > 0:
            text.write('%s\n\n' % self.header)

        self.generateBody(text)

        if len(self.footer) > 0:
            text.write('\n\n%s' % self.footer)

        text.seek(0)
        body = text.read()

        if self.isTesting():
            self.dumpToTestFile(body)
        else:
            smtp = SMTP(self.server)
            if self.username is not None:
                smtp.login(self.username, self.password)
            smtp.sendmail(self['from'], self.to, body)
            smtp.quit()

class ApacheStyleEmailView(BaseEmailView):
    """Sends out an email formatted in a style mimicking Apace commit emails."""
    pass

class TigrisStyleEmailView(BaseEmailView):
    """Sends out an email formatted in a style mimicking Tigris commit emails."""

    def printFiles(self, text, action):
        directories = self.model.directoriesWithFiles(action)
        if len(directories) > 0:
            text.write('%s%s:\n' % (action[0].upper(), action[1:]))
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

        text.write('Log:\n')
        lines = self.model.log().split('\n')
        for line in lines:
            text.write(' %s\n' % line)
        text.write('\n')

        text.write('File Changes:\n\n')
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

