#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
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
        self.cc = ''
        self.rfc_header = ''

    def __getitem__(self, name):
        """Used to get the 'from' attribute (as it is a keyword)"""
        return self.__dict__[name]

    def execute(self):
        """Sends the email with commit information"""
        text = StringIO('')
        text.write('To: %s\n' % self.to)

        if len(self.cc) > 0:
            text.write('Cc: %s\n' % self.cc)

        text.write('From: %s\n' % self['from'])
        text.write('Subject: %s\n' % self.subject.split('\n')[0])
        text.write('Date: %s -0000 (GMT)\n' % time.strftime('%A %d %B %Y %H:%M:%S', time.gmtime()))

        if len(self.rfc_header) > 0:
            text.write('%s\n' % self.rfc_header)

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
        elif len(self.server) > 0:
            smtp = SMTP(self.server)
            if self.username is not None:
                smtp.login(self.username, self.password)
            smtp.sendmail(
                self['from'],
                filter(lambda x: x != '', [addr.strip() for addr in self.to.split(',')] + [addr.strip() for addr in self.cc.split(',')]),
                body)
            smtp.quit()
        else:
            print 'No server provided, not sending an email.'

class ApacheStyleEmailView(BaseEmailView):
    """Sends out an email in a style mimicking the U{Apache<http://www.apache.org>} commit email format (not implemented)"""
    pass

class HtmlEmailView(BaseEmailView):
    """Sends out an email in a style using HTML tables for better readability with variable-width font (not implemented)"""
    pass

class TigrisStyleEmailView(BaseEmailView):
    """Sends out an email in a style mimicking the U{Tigris<http://www.tigris.org>} commit email format

    This view has several properties:

     - server (required) - the mail server to relay through
     - subject (required) - the subject line (e.g. "commit: $model.greatestCommonDirectory()")
     - from (required) - the from email address (e.g. "$model.user@yourdomain.com")
     - to (required) - a comma-separated list of email addresses to send to
     - cc (optional) - a comma-separated list of email addresses to cc to
     - header (optional) - text to put at the beginning of the email
     - footer (optional) - text to put at the end of the email
    """

    def printFilesAndDirectories(self, text, action):
        # This needs to handle printing both directories with no files in them and directories with files in them
        dirs1 = self.model.directories(action)
        dirs2 = self.model.directoriesWithFiles(action)

        # Merge the two
        dirs = dirs1 + [dir for dir in dirs2 if dir not in dirs1]
        dirs.sort()

        if len(dirs) > 0:
            text.write('%s%s:\n' % (action[0].upper(), action[1:]))
            for dir in dirs:
                text.write(' %s\n' % dir.path)

                files = dir.filesByAction(action)
                if len(files) > 0:
                    text.write('  ' + ', '.join([file.name for file in files]) + '\n')

            text.write('\n')

    def generateBody(self, text):
        """@return: a string for the body of the email"""
        text.write('User: %s\n' % self.model.user)
        text.write('Date: %s\n' % time.strftime('%Y/%m/%d %I:%M %p'))
        text.write('\n')

        self.printFilesAndDirectories(text, 'added')
        self.printFilesAndDirectories(text, 'removed')
        self.printFilesAndDirectories(text, 'modified')

        text.write('Log:\n')
        for line in self.model.log.split('\n'):
            text.write(' %s\n' % line)
        text.write('\n')

        dirsWithDiffs = [d for d in self.model.directories() if d.diff]
        if len(dirsWithDiffs) > 0:
            text.write('Directory Changes:\n\n')
            for dir in dirsWithDiffs:
                s = 'Directory: %s' % dir.path
                line = ''.join(['='] * len(s))
                text.write('%s\n%s\n\n' % (s, line))
                text.write(dir.diff)
            text.write('\n')

        if len(self.model.directoriesWithFiles()) > 0:
            text.write('File Changes:\n\n')
            for dir in self.model.directoriesWithFiles():
                s = 'Directory: %s' % dir.path
                line = ''.join(['='] * len(s))
                text.write('%s\n%s\n\n' % (s, line))

                for file in dir.files:
                    text.write('File [%s]: %s\n' % (file.action, file.name))
                    text.write('Delta lines: %s\n' % file.delta)
                    text.write('%s\n' % file.diff)

class InlineAttachmentEmailView(BaseEmailView):
    """Sends out an email with the diff of the commit attached as a file

    This view has several properties:

     - server (required) - the mail server to relay through
     - subject (required) - the subject line (e.g. "commit: $model.greatestCommonDirectory()")
     - from (required) - the from email address (e.g. "$model.user@yourdomain.com")
     - to (required) - a comma-separated list of email addresses to send to
     - header (optional) - text to put at the beginning of the email
     - footer (optional) - text to put at the end of the email

    Contributed by Juan F. Codagnone <juam@users.sourceforge.net>
    """

    def __init__(self, name, model):
        """Initializes the the username to None, header, footer, and rfc_header

        The username is default to None, header to 'This is a multi-part message
        in MIME format.', footer to '' and rfc_header to the MIME boundary.
        """

        BaseEmailView.__init__(self, name, model)

        self.boundary = 'Boundary-00=_Ij9UAWIepv2oFVA'
        self.header = 'This is a multi-part message in MIME format.'
        self.rfc_header = \
            'MIME-Version: 1.0\n' \
            'Content-Type: Multipart/Mixed;\n' \
            ' boundary="%s"' % (self.boundary)

    def generateBody(self, text):
        """Generates the email with the patch inlined

        Should probably use the email.MIMEImage module, but this just works.
        """

        # First write out the body of the email with the log and list of changed files
        text.write(
            '--%s\n'
            'Content-Type: text/plain;\n'
            ' charset="US-ASCII"\n'
            'Content-Transfer-Encoding: 7bit\n'
            'Content-Disposition: inline\n\n' % self.boundary)

        text.write('Log:\n')
        for line in self.model.log.split('\n'):
            text.write(' %s\n' % line)
        text.write('\n')

        for dir in self.model.directoriesWithFiles():
            for file in dir.files:
                text.write(' * %s %s\n' % (file.action.upper(), file.path))


        # Second write out the patch file
        filename = 'rev-%s.diff' % (self.model.rev)

        text.write(
            '\n'
            '--%s\n'
            'Content-Type: text/x-diff;\n'
            ' charset="US-ASCII"\n'
            ' name="%s"'
            'Content-Transfer-Encoding: 8bit\n'
            'Content-Disposition: inline;\n'
            ' filename="%s"\n\n' % (self.boundary, filename, filename))

        for dir in self.model.directoriesWithFiles():
            for file in dir.files:
                text.write('File [%s]: %s\tDelta lines: %s\n' % (file.action, file.path, file.delta))
                text.write('%s\n' % file.diff)

        text.write('--%s--\n' % self.boundary)

