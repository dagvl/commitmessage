#!/usr/bin/perl -w
#
# commitmessage_loginfo.pl
# commitmessage Version 1.0
# Copyright 2002 Stephen Haberman
#
# Perl filter to handle the log messages from the checkin of files in
# a directory. This script will group the lists of files by log
# message, and mail a single consolidated log message at the end of
# the commit.
#
# This file assumes a pre-commit checking program that leaves the
# names of the first and last commit directories in a temporary file.
#
# Contributed by David Hampton <hampton@cisco.com>
# Roy Fielding removed useless code and added log/mail of new files
# Ken Coar added special processing (i.e., no diffs) for binary files
#
# Adapted from the Apache mail scripts (comments above) for use in Scarab
# <http://scarab.tigris.org> by Stephen Haberman <stephenh@chase3000.com> and
# evolved into an module, OO-based system.
#
# Major changes made by Stephen:
#
# - MVC-ized the view out to ViewXxx scripts that work off the $model and
# the commitmessage.config file.
#
# - Removed $LOG_FILE because we assume the entire commit has only
# one message
#
# - Removed $SUMMARY_FILE and instead store diffs in a separate temp file 
# for each added/modified file
#
# The $model structure:
#
#   user = the user who ran the commit, e.g. "bob"
#   module = the name of the module, e.g. "CVSROOT"
#   files = a hash of all the files in the commit, with the key
#      being the path relative to the module, e.g. "commitinfo"
#
#      The value of each key in the hash is itself a hash with
#      the follow properties:
#      
#      action = why the file is in the commit, e.g. "added"/"removed"/"modified"/"branch"
#      rev = the new revision, e.g. 1.3
#      delta = the number of line changes, e.g. +1/-4
#      rcsfile = the path of the file for rcs
#      diff = for added and modified files, contains the diff that resulted from the commit
#
# In the View packages, you can loop through the files in the $model structure like:
#
#   foreach my $file (keys %{$model->files}}) {
#      my $action = $model->{files}{$file}{action};
#      ...
#   }
#

use lib "$ENV{CVSROOT}/CVSROOT/commitmessage";
use Controller;
use strict;

#
# Initialize the and run the Controller
#
my $controller = Controller->new();
$controller->parseArgv(@ARGV);
$controller->main;

