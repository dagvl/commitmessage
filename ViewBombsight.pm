#!/usr/bin/perl -w
#
# ViewBombsight.pm
# Version 0.9
#
# Sample script that sends out notification of bug-related commits
# to Bombsight.
#
# (Bombsight is a slight modification to the bug tracking system
# FogBUGZ <http://www.fogcreek.com/FogBUGZ/>).
#

package ViewBombsight;
use Socket;
use strict;

#
# Creates a new view object.
#
sub new {
    my($type, $props, $om) = @_;
    my $self = {};
    bless($self, $type);

    # Copy over props, and eval them
    foreach my $key (keys %$props) {
        eval("\$self->{$key} = \"$props->{$key}\"");
    }

    return $self;
}

#
# Do nothing on a newdir
#
sub newdir {
    my($self, $om) = @_;

    return;
}

#
# Post the details of each affected files to Bombsight
#
sub commit {
    my($self, $om) = @_;

    # Get the bug id
    my $bugId = 0;
    my $log = $om->{log};

    if ($log =~ /b(0|o)mb((site)|(sight)):\s*([0-9]*)/i) {
        $bugId = int($5);
        print "Adding bug info for bug $bugId...\n";
    }
    elsif ($log =~ /fogbug[sz]?\s*id\s*:\s*([0-9]*)/i) {
        $bugId = int($1);
        print "Adding bug info for bug $bugId...\n";
    }

    if ($bugId > 0) {
        foreach my $file (keys %{$om->{files}}) {
            my $action = $om->{files}{$file}{action};

            my $get = "";
            $get .= "GET $self->{url}$self->{page}";
            $get .= "?ixBug=$bugId";
            $get .= "&sFile=/$om->{module}/$file";
            $get .= "&sPrev=$om->{files}{$file}{prev_rev}";
            $get .= "&sNew=$om->{files}{$file}{rev}";
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
