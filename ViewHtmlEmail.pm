#!/usr/bin/perl -w
#
# ViewHtmlEmail.pm
# commitmessage version 0.9
#
# Simple email script that acts as a view for the MVC-based
# commitmessage script.
#
# TODO: 
#
# - Move the bug id replacement stuff to the config file
#

package ViewHtmlEmail;
use strict;

my @DAYS = ( 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday' );
my @MONTHS = ( 'January', 'Febuary', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December' );

#
# Creates a new view object.
#
sub new {
    my($type, $props, $om) = @_;
    my $self = {};
    bless($self, $type);

    # Copy over props, and eval them
    foreach my $key (keys %$props) {
        # Delay evaling the logReplaceResult
        if ($key eq "logReplaceResult") {
            $self->{$key} = $props->{$key};
        }
        else {
            eval("\$self->{$key} = \"$props->{$key}\"");
        }
    }

    my @time = gmtime();
    $self->{shortdatetime} = sprintf("%s %s %s %s %s:%s:%s", 
        $DAYS[$time[6]], $time[3], $MONTHS[$time[4]],
        $time[5] + 1900, $time[2], $time[1], $time[0]);
    $self->{datetime} = "$self->{shortdatetime} -0000 (GMT)";

    return $self;
}

#
# Send a simple email on newdir creation
#
sub newdir {
    my($self, $om) = @_;

    $self->sendmail($om, "<p>$om->{user} created $om->{newdir}</p>");
}

#
# Send a list of affected files and diffs on commit
#
sub commit {
    my($self, $om) = @_;

    # First remove all of the <, >, and \n
    my $log = $self->formatlog($om->{log});

    # Basic header    
    my $text = "<p>$om->{user} committed the following changes on $self->{shortdatetime}.</p>";

    # Create the the table header
    $text .= "<p>\n";
    $text .= "<table border=1 cellspacing=0>\n";
    $text .= "   <tr>\n";
    $text .= "      <td colspan=5>&nbsp;<br>$log<br>&nbsp;<br></td>\n";
    $text .= "   </tr>\n";
    $text .= "   <tr>\n";
    $text .= "      <td><center>File</center></td>\n";
    $text .= "      <td><center>Rev</center></td>\n";
    $text .= "      <td><center>Lines</center></td>\n";
    $text .= "      <td><center>State</center></td>\n";
    $text .= "   </tr>\n";

    # Give a one-line description for each file
    foreach my $file (sort keys %{$om->{files}}) {
        my $action = $om->{files}{$file}{action};

        $text .= "   <tr>\n";

        if (defined($self->{cvsweb})) {
            $text .= "      <td><nobr><a href=\"$self->{cvsweb}/$om->{module}/$file\">$file</a>&nbsp;</nobr></td>\n";
        }
        else {
            $text .= "      <td><nobr>$file&nbsp;</nobr></td>\n";
        }

        $text .= "      <td><center>$om->{files}{$file}{rev}</center></td>\n";
        $text .= "      <td><nobr><center>$om->{files}{$file}{delta}</center></nobr></td>\n";
        $text .= "      <td><center>$action</center></td>\n";
        $text .= "   </tr>\n";
    }

    $text .= "</table></p>\n\n";

    # Go through the diffs of the added/modified files
    $text .= "<p>Diffs:</p>\n";
    foreach my $file (sort keys %{$om->{files}}) {
        my $action = $om->{files}{$file}{action};
        if ($action eq "added" || $action eq "modified") {
            my $diff = $om->{files}{$file}{diff};
            $diff = $self->toHtml($diff);

            $text .= "<p><pre>$diff</pre></p>&nbsp<br />\n";
        }
    }

    $text .= "\n\n";

    $self->sendmail($om, $text);
}

#
# Format the log to HTML and handle bug links
#
sub formatlog {
    my($self, $log) = @_;

    $log = $self->toHtml($log);

    if (defined($self->{logReplacePattern})) {
        $log =~ /$self->{logReplacePattern}/i;
        my $replace = "";
        eval("\$replace = \"$self->{logReplaceResult}\";");
        $log =~ s/$self->{logReplacePattern}/$replace/i;
    }

    return $log;
}

#
# Convert <, >, \n to HTML
#
sub toHtml {
    my($self, $text) = @_;

    $text =~ s/</&lt;/g;
    $text =~ s/>/&gt;/g;
    $text =~ s,\n,&nbsp;<br />,g;

    return $text;
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