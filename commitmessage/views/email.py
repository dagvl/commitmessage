#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""Provides an email L{commitmessage.model.View}s"""

import os
import sys
import time

from StringIO import StringIO
from smtplib import SMTP
from commitmessage.model import View

class BaseEmailView(View):
    """A basic email implementation for other style-specific email views to extend
    """

    def __init__(self, name, model):
        """Initializes the the SMTP username to None, header to '', and footer to ''"""
        View.__init__(self, name, model)

        self.username = None
        self.header = ''
        self.footer = ''

    def __getitem__(self, name):
        """Used to get the 'from' attribute (as it is a keyword)"""
        return self.__dict__[name]

    def execute(self):
        """Sends the email with commit information"""
        text = StringIO('')
        text.write('To: %s\n' % self.to)
        text.write('From: %s\n' % self['from'])
        text.write('Subject: %s\n' % self.subject.split('\n')[0])
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
            smtp.sendmail(
                self['from'],
                [addr.strip() for addr in self.to.split(',')],
                body)
            smtp.quit()

class ApacheStyleEmailView(BaseEmailView):
    """Sends out an email in a style mimicking U{Apache<http://www.apache.org>} commit emails (not implemented)"""
    pass

class HtmlEmailView(BaseEmailView):
    """Sends out an email in a style using HTML tables for better readability with variable-width font (not implemented)"""
    pass

class TigrisStyleEmailView(BaseEmailView):
    """Sends out an email in a style mimicking U{Tigris<http://www.tigris.org>} commit email format

    This view has several properties:

     - server (required) - the mail server to relay through
     - subject (required) - the subject line (e.g. "commit: $model.greatestCommonDirectory()")
     - from (required) - the from email address (e.g. "$model.user@yourdomain.com")
     - to (required) - a comma-separated list of email addresses to send to
     - header (optional) - text to put at the beginning of the email
     - footer (optional) - text to put at the end of the email
    """

    def printFiles(self, text, action):
        directories = self.model.directoriesWithFiles(action)
        if len(directories) > 0:
            text.write('%s%s:\n' % (action[0].upper(), action[1:]))
            for dir in directories:
                text.write(' %s\n' % dir.path)
                files = dir.filesByAction(action)
                text.write('  %s' % files[0].name)
                for file in files[1:]:
                    text.write(', %s' % file.name)
                text.write('\n')
            text.write('\n')

    def generateBody(self, text):
        """@return: a string for the body of the email"""
        text.write('User: %s\n' % self.model.user)
        text.write('Date: %s\n' % time.strftime('%Y/%m/%d %I:%M %p'))
        text.write('\n')

        self.printFiles(text, 'added')
        self.printFiles(text, 'removed')
        self.printFiles(text, 'modified')

        text.write('Log:\n')
        lines = self.model.log.split('\n')
        for line in lines:
            text.write(' %s\n' % line)
        text.write('\n')

        text.write('File Changes:\n\n')
        for dir in self.model.directoriesWithFiles():
            s = 'Directory: %s' % dir.path
            line = ''
            for i in range(0, len(s)):
                line = line + '='
            text.write('%s\n%s\n\n' % (s, line))

            for file in dir.files:
                text.write('File [%s]: %s\n' % (file.action, file.name))
                text.write('Delta lines: %s\n' % file.delta)
                text.write('%s\n' % file.diff)

