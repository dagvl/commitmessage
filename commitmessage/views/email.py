#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2004 Stephen Haberman
#

"""Provides an email L{commitmessage.model.View}s"""

import os
import sys
import time

from io import StringIO
from smtplib import SMTP
from commitmessage.model import View

def formatdate(timeval=None):
    """Returns time format preferred for Internet standards.

    Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123

    According to RFC 1123, day and month names must always be in
    English.  If not for that, this code could use strftime().  It
    can't because strftime() honors the locale and could generate
    non-English names.
    """
    if timeval is None:
        timeval = time.time()
    timeval = time.gmtime(timeval)
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
            ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[timeval[6]],
            timeval[2],
            ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")[timeval[1]-1],
             timeval[0], timeval[3], timeval[4], timeval[5])

class BaseEmailView(View):
    """A basic email implementation for other style-specific email views to extend

    Core properties:

     - server (required) - the mail server to relay through
     - subject (required) - the subject line (e.g. "commit: $model.greatestCommonDirectory()")
     - from (required) - the from email address (e.g. "$model.user@yourdomain.com")
     - to (required) - a comma-separated list of email addresses to send to
     - cc (optional) - a comma-separated list of email addresses to cc to
     - header (optional) - text to put at the beginning of the email
     - footer (optional) - text to put at the end of the email

     - username - a SMTP auth username
     - password - a SMTP auth password
     - contenttype - the Content-Type header to use (defaults to: text/plain; charset="iso-8859-1")
    """

    def __init__(self, name, model):
        """Initializes the the SMTP username to None, header to '', and footer to ''"""
        View.__init__(self, name, model)

        self.username = None
        self.header = ''
        self.footer = ''
        self.cc = ''
        self.contenttype = 'text/plain; charset="iso-8859-1"'
        self.otherHeaders = {}

    def __getitem__(self, name):
        """Used to get the 'from' attribute (as it is a keyword)"""
        return self.__dict__[name]

    def generateSubject(self, text):
        text.write('Subject: %s\n' % self.subject.split('\n')[0])

    def execute(self):
        """Sends the email with commit information"""

        text = StringIO('')
        text.write('To: %s\n' % self.to)

        if len(self.cc) > 0:
            text.write('Cc: %s\n' % self.cc)

        text.write('From: %s\n' % self['from'])
        self.generateSubject(text)
        text.write('Date: %s\n' % formatdate())
        text.write('Content-Type: %s\n' % self.contenttype)

        for name, value in list(self.otherHeaders.items()):
            text.write('%s: %s\n' % (name, value))

        # Done with header, final extra \n
        text.write('\n')

        # User-defined body text header
        if len(self.header) > 0:
            text.write('%s\n\n' % self.header)

        # Sub classes must implement this
        self.generateBody(text)

        # User-defined body text footer
        if len(self.footer) > 0:
            text.write('\n\n%s' % self.footer)

        text.seek(0)
        body = text.read().encode("ascii", "replace")

        if self.isTesting():
            self.dumpToTestFile(body)
        elif len(self.server) > 0:
            smtp = SMTP(self.server)
            if self.username is not None:
                smtp.login(self.username, self.password)
            smtp.sendmail(
                self['from'],
                [x for x in [addr.strip() for addr in self.to.split(',')] + [addr.strip() for addr in self.cc.split(',')] if x != ''],
                body)
            smtp.quit()
        else:
            print('No server provided, not sending an email.')

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
        self.contenttype = 'Multipart/Mixed;\n boundary="%s"' % (self.boundary)
        self.otherHeaders['MIME-Version'] = '1.0'

        # Use the user-defined header to output this generic MIME message that
        # most email clients won't show
        self.header = 'This is a multi-part message in MIME format.'

    def generateBody(self, text):
        """Generates the email with the patch inlined

        Should probably use the email.MIMEImage module, but this just works.
        """

        # First write out the body of the email with the log and list of changed files
        text.write(
            '--%s\n'
            'Content-Type: text/plain;\n charset="US-ASCII"\n'
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
            'Content-Type: text/x-diff;\n charset="US-ASCII"\n name="%s"'
            'Content-Transfer-Encoding: 8bit\n'
            'Content-Disposition: inline;\n'
            ' filename="%s"\n\n' % (self.boundary, filename, filename))

        for dir in self.model.directoriesWithFiles():
            for file in dir.files:
                text.write('File [%s]: %s\tDelta lines: %s\n' % (file.action, file.path, file.delta))
                text.write('%s\n' % file.diff)

        text.write('--%s--\n' % self.boundary)


class EtherealStyleEmailView(BaseEmailView):
    """Sends out an email in the Ethereal commit message style.

    The log message is followed by a list of file deltas.  This provides useful
    change information without blasting the recipient(s) with multimegabyte
    diffs.

    This view has several properties:

     - server (required) - the mail server to relay through
     - subject (required) - the subject line (e.g. "commit: $model.greatestCommonDirectory()").  A list of directories/files will be appended.
     - from (required) - the from email address (e.g. "$model.user@yourdomain.com")
     - to (required) - a comma-separated list of email addresses to send to
     - header (optional) - text to put at the beginning of the email
     - footer (optional) - text to put at the end of the email
     - maxfiles (optional) - the maximum number of files to list

    Contributed by Gerald Combs <gerald [AT] ethereal.com>
    """

    def __init__(self, name, model):
        """Initializes the the username to None, header, footer, and rfc_header

        The username is default to None, header to 'This is a multi-part message
        in MIME format.', footer to '' and rfc_header to the MIME boundary.
        """

        BaseEmailView.__init__(self, name, model)

        self.maxfiles = '-1'

    def generateSubject(self, text):
        """Wrap the subject at 75 characters, and cap it at three lines.
        Append "..." if the subject is truncated.
        """
        cur_line = 'Subject: %s' % self.subject.split('\n')[0]
        subj_lines = []
        more_files = 0

        for dir in self.model.directoriesWithFiles():
            append = ' ' + dir.path + ':'
            if len(cur_line) + len(append) > 75:
                if len(subj_lines) > 1:
                    more_files = 1
                    break
                else:
                    subj_lines.append(cur_line)
                    cur_line = ''
            cur_line = cur_line + append
            for file in dir.files:
                append = ' ' + file.name
                if len(cur_line + append) > 75:
                    if len(subj_lines) > 1:
                        more_files = 1
                        break;
                    else:
                        subj_lines.append(cur_line)
                        cur_line = ''
                cur_line = cur_line + append

        if (more_files):
            cur_line = cur_line + ' ...'
        subj_lines.append(cur_line)
        text.write('\n'.join(subj_lines))
        text.write('\n')

    def generateBody(self, text):
        """@return: a string for the body of the email"""
        files_remaining = 0
        files_max = int(self.maxfiles)

        for dir in self.model.directoriesWithFiles():
            files_remaining = files_remaining + len(dir.files)
        file_limit = files_remaining - files_max

        text.write('User: %s\n' % self.model.user)
        text.write('Date: %s\n' % time.strftime('%Y/%m/%d %I:%M %p'))
        text.write('\n')

        text.write('Log:\n')
        for line in self.model.log.split('\n'):
            text.write(' %s\n' % line)
        text.write('\n')

        for dir in self.model.directoriesWithFiles():
            if (files_max > 0 and files_remaining <= file_limit):
                break
            text.write('Directory: %s\n' % (dir.path))

            max_name_len = 10
            for file in dir.files:
                if len(file.name) > max_name_len: max_name_len = len(file.name)
            fmtstr = '  %%-10s %%-%ds    %%s\n' % (max_name_len)
            text.write(fmtstr % ('Changes', 'Path', 'Action'))

            for file in dir.files:
                action = file.action[0].upper() + file.action[1:]
                text.write(fmtstr % (file.delta, file.name, action))
                if (files_max > 0):
                    files_remaining = files_remaining - 1
                if (files_remaining < file_limit):
                    break

            text.write('\n')

        if files_max > 0 and files_remaining:
            if files_remaining > 1:
                plurality = 's'
            else:
                plurality = ''
            text.write('\n')
            text.write('(%d file%s not shown)' % (files_remaining, plurality))

