#!/usr/bin/perl -w
#
# ViewBombsight.pm
# commitmessage Version 1.0-beta1
#
# Sample script that sends out notification of bug-related commits
# to Bombsight.
#
# (Bombsight is a slight modification to the bug tracking system
# FogBUGZ <http://www.fogcreek.com/FogBUGZ/>).
#

package ViewBombsight;
use ViewBase;
use Socket;
@ISA = qw(ViewBase);
use strict;

#
# Post the details of each affected files to Bombsight
#
sub commit {
    my($self, $model) = @_;

    # Get the bug id
    my $bugId = 0;
    my $log = $model->{log};

    if ($log =~ /b(0|o)mb((site)|(sight)):\s*([0-9]*)/i) {
        $bugId = int($5);
        print "Adding bug info for bug $bugId...\n";
    }
    elsif ($log =~ /fogbug[sz]?\s*id\s*:\s*([0-9]*)/i) {
        $bugId = int($1);
        print "Adding bug info for bug $bugId...\n";
    }

    if ($bugId > 0) {
        foreach my $file ($model->fileKeysSorted) {
            my $action = $model->files->{$file}{action};

            my $get = "";
            $get .= "GET $self->{url}$self->{page}";
            $get .= "?ixBug=$bugId";
            $get .= "&sFile=/$file";
            $get .= "&sPrev=" . $model->files->{$file}{prev};
            $get .= "&sNew=" . $model->files->{$file}{rev};
            $get .= " HTTP/1.1\n";

            $get .= "Host: $self->{server}:$self->{port}\n\n";

##            print "GET = \n$get";

            my $in_addr = (gethostbyname($self->{server}))[4] || die("Error: $!\n");
            my $paddr = sockaddr_in($self->{port}, $in_addr) || die("Error: $!\n");
            socket(S, PF_INET, SOCK_STREAM, getprotobyname('tcp')) || die("Error: $!\n");
            connect(S, $paddr) || die("Error: $!\n");
            select(S);
            $|=1;
            select(STDOUT);
            print S $get;
            close(S);
        }
    }
}

1;
