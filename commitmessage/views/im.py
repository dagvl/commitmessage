#!/usr/bin/env python
#
# commitmessage
# Copyright 2002-2003 Stephen Haberman
#

"""Provides an AIM L{commitmessage.model.View}s"""

import time

from StringIO import StringIO
from toc import TocTalk, BotManager
import msnp

from commitmessage.model import View

class IMView(View):
    """An abstract class to hold the message-generation logic for IM clients"""

    # Borrowed from email.py
    def _printFiles(self, text, action):
        directories = self.model.directoriesWithFiles(action)
        if len(directories) > 0:
            text.write('%s%s:\n' % (action[0].upper(), action[1:]))
            for dir in directories:
                text.write(' %s' % dir.path)
                files = dir.filesByAction(action)
                text.write('%s' % files[0].name)
                for file in files[1:]:
                    text.write(', %s' % file.name)
                text.write('\n')

    def _generateMessage(self):
        text = StringIO('')

        text.write(self.model.user)
        text.write('\n')
        text.write(self.model.log)
        text.write('\n')

        self._printFiles(text, 'added')
        self._printFiles(text, 'removed')
        self._printFiles(text, 'modified')

        text.seek(0)
        return text.read()

class MSNView(IMView):
    """Send out commit messages on MSN

    This view has three properties:

     - passport - the MSN passport to login with
     - password - the password for the MSN passport
     - to - a comma-separated list of other MSN passports to send the message to
    """

    def execute(self):
        """Sends the IM with the commit message"""

        class MsnListener(msnp.SessionCallbacks):
            def __init__(self, message):
                self._message = message
                self._done = False
            def chat_started(self, chat):
                chat.send_message(self._message)
                self._done = True

        listener = MsnListener(self._generateMessage())
        msn = msnp.Session(listener)

        msn.login(self.passport, self.password)

        for name in [name.strip() for name in self.to.split(',')]:
            msn.start_chat(name)
            listener._done = False

            while not listener._done:
                msn.process(chats=True)
                time.sleep(1)

class AIMView(IMView):
    """Send out stuff on AIM

    This view has three properties:

     - screenname - the AIM screenname to login with
     - password - the password for AIM screenname
     - to - a comma-seperated list of other AIM screennames to send the message to
    """

    def execute(self):
        """Sends the IM with the commit message"""

        bm = BotManager()
        bot = TocTalk(self.screenname, self.password)

        bm.addBot(bot, "bot")
        time.sleep(4)

        message = self._generateMessage()

        names = [name.strip() for name in self.to.split(',')]
        for name in names:
            print name
            bot.do_SEND_IM(name, message)

