#!/usr/bin/perl
#
# commitmessage_commitinfo.pl
# Version 0.9
#
# Perl filter to handle pre-commit checking of files.  This program
# records the last directory where commits will be taking place for
# use by the log_accum.pl script.
#
# Contributed by David Hampton <hampton@cisco.com>
# Stripped to minimum by Roy Fielding
#
############################################################

$id = getpgrp();
$TMPDIR = $ENV{'TMPDIR'} || '/tmp';
$FILE_PREFIX = "#cvs.$id.";

# MUST match log_accum.pl
$LAST_FILE = "$TMPDIR/${FILE_PREFIX}lastdir";

sub write_line {
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

&write_line("$LAST_FILE", $ARGV[0]);

exit(0);
