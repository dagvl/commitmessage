#!/usr/bin/perl -w
#
# CvsUtil.pm
# commitmessage Version 0.91
#
# Executes and parsers a few generic cvs commands.
#

package CvsUtil;
use Controller;
use strict;

#
# Return the rev, delta, and rcsfile for a file
#
# Params: file
#
sub status {
    my($type, $file) = @_;

    my $rev = "";
    my $delta = "";
    my $rcsfile = "";

    my $cvsroot = Controller->CVSROOT;

    open(RCS, "-|") || exec 'cvs', '-Qn', 'status', $file;
    while (<RCS>) {
        if (/^[ \t]*Repository revision/) {
            chomp;
            my @revline = split(' ', $_);
            $rev = $revline[2];
            $rcsfile = $revline[3];
            $rcsfile =~ s,^$cvsroot/,,;
            $rcsfile =~ s/,v$//;
        }
    }
    close(RCS);

    if ($rev ne '' && $rcsfile ne '') {
        open(RCS, "-|") || exec 'cvs', '-Qn', 'log', "-r$rev", $file;
        while (<RCS>) {
            if (/^date:/) {
                chomp;
                $delta = $_;
                $delta =~ s/^.*;//;
                $delta =~ s/^[\s]+lines://;
            }
        }
        close(RCS);
    }

    return ($rev, $delta, $rcsfile);
}

#
# Return the diff for the given file
#
# Params: file, current revision
#
sub diff {
    my($type, $file, $rev) = @_;
    my $diff = "";

    #
    # If this is a binary file, don't try to report a diff; not only is
    # it meaningless, but it also screws up some mailers. We rely on
    # Perl's 'is this binary' algorithm; it's pretty good. But not
    # perfect.
    #

    if (($file =~ /\.(?:pdf|gif|jpg|mpg)$/i) || (-B $file)) {
        $diff .= "<<Binary file>>";
    }
    else {
        #
        # Get the differences between this and the previous revision,
        # being aware that new files always have revision '1.1' and
        # new branches always end in '.n.1'.
        #
        my $prev = CvsUtil->calculatePreviousRevision($rev);

        if ($rev eq '1.1') {
            open(DIFF, "-|") || exec 'cvs', '-Qn', 'update', '-p', '-r1.1', $file;
            $diff .= "Index: $file\n=================================="
                . "=================================\n";
        }
        else {
            open(DIFF, "-|") 
                || exec 'cvs', '-Qn', 'diff', '-u', "-r$prev", "-r$rev", $file;
        }

        while (<DIFF>) {
            $diff .= $_;
        }

        close(DIFF);
    }

    return $diff;
}

#
# Return the previous revision
#
# Params: the current revision
#
sub calculatePreviousRevision {
    my($type, $rev) = @_;
    my $prev = "";

    if ($rev =~ /^(.*)\.([0-9]+)$/) {
        my $prev_temp = ($2 - 1);
        $prev = $1 . '.' . $prev_temp;

        # Truncate if first rev on branch
        $prev =~ s/\.[0-9]+\.0$//;
    }

    return $prev;
}

1;