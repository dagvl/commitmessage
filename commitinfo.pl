#!/usr/bin/perl
#
# commitinfo.pl
# commitmessage Version 0.91
#
# Perl filter to handle pre-commit checking of files.  This program
# records the last directory where commits will be taking place for
# use by the log_accum.pl script.
#
# Contributed by David Hampton <hampton@cisco.com>
# Stripped to minimum by Roy Fielding
#
############################################################

# MUST match loginfo.pl
$id = getpgrp();
$TMPDIR = $ENV{'TMPDIR'} || '/tmp';
$FILE_PREFIX = "#cvs.$id.";
$LAST_FILE = "$TMPDIR/${FILE_PREFIX}lastdir";

sub writeLine {
    local($filename, $line) = @_;

    open(FILE, ">$filename") || die("Cannot open $filename: $!\n");
    print(FILE $line, "\n");
    close(FILE);
}

#
# Record this directory as the last one checked. This will be used
# by the log_accumulate script to determine when it is processing
# the final directory of a multi-directory commit.
#

&writeLine("$LAST_FILE", $ARGV[0]);

exit(0);
