#!/usr/bin/perl -w
#
# ViewEmail.pm
# commitmessage version 0.9
#
# Simple email script that acts as a view for the MVC-based
# commitmessage script.
#
# TODO: 
#
# - Move the bug id replacement stuff to the config file
#

package ViewEmail;
use ViewBase;
@ISA = qw(ViewBase);
use strict;

my @DAYS = ( 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday' );
my @MONTHS = ( 'January', 'Febuary', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December' );

#
# Creates a new view object.
#
sub init {
    my($self, $model) = @_;

    my @time = gmtime();
    $self->{shortdatetime} = sprintf("%s %s %s %s %s:%s:%s", 
        $DAYS[$time[6]], $time[3], $MONTHS[$time[4]],
        $time[5] + 1900, $time[2], $time[1], $time[0]);
    $self->{datetime} = "$self->{shortdatetime} -0000 (GMT)";
}

#
# Send a simple email on newdir creation
#
sub newDirectory {
    my($self, $om) = @_;

    $self->sendmail($om, "$om->{user} created $om->{newdir}");
}

#
# Send a list of affected files and diffs on commit
#
sub commit {
    my($self, $om) = @_;

    # First remove all of the <, >, and \n
    my $log = $self->formatlog($om->{log});

    # Basic header    
    my $text = "$om->{user} committed the following changes on $self->{shortdatetime}.\n\n";

    # Create the the table header
    $text .= "$log\n\n";
    
    # Give a one-line description for each file
    foreach my $file (sort keys %{$om->{files}}) {
        my $action = $om->{files}{$file}{action};

        $text .= "$file\n";
        $text .= "$om->{files}{$file}{rev}\n";
        $text .= "$om->{files}{$file}{delta}\n";
        $text .= "$action\n\n";
    }

    # Go through the diffs of the added/modified files
    $text .= "Diffs:</p>\n\n";
    foreach my $file (sort keys %{$om->{files}}) {
        my $action = $om->{files}{$file}{action};
        if ($action eq "added" || $action eq "modified") {
            $text .= "$om->{files}{$file}{diff}\n\n";
        }
    }

    $text .= "\n\n";

    $self->sendmail($om, $text);
}

#
# Format the log to HTML and handle bombsight links
#
sub formatlog {
    my($self, $log) = @_;

    if (defined($self->{logReplacePattern})) {
##        print "pattern: $self->{logReplacePattern}\n";
##        print "result: $self->{logReplaceResult}\n";
        $log =~ s/$self->{logReplacePattern}/$self->{logReplaceResult}/i;
    }

    return $log;
}

#
# Perform the sendmail operation
#
sub sendmail {
    my($self, $om, $text) = @_;

    # Don't send if 'to' is not set
    if (!defined($self->{to})) {
        print "Skipping cvs email...\n";
        return;
    }

    print "Sending cvs email...\n";

    open(MAIL, "|$self->{sendmail}") || die("could not open mail '$self->{sendmail}': $!");

    print MAIL "To: $self->{to}\n";
    print MAIL "From: $self->{from}\n";
    print MAIL "Subject: $self->{subject}\n";
    print MAIL "MIME-Version: 1.0\n";
    print MAIL "Content-Type: text/html\n";
    print MAIL "Date: " . $self->{datetime} . "\n\n";

    print MAIL $self->{header};
    print MAIL $text;
    print MAIL $self->{footer};

    close(MAIL);
}

1;