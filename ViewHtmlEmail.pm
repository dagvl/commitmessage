#!/usr/bin/perl -w
#
# ViewHtmlEmail.pm
# commitmessage Version 0.91
#
# Simple email script that acts as a view for the MVC-based
# commitmessage script.
#
# TODO: 
#
# - Move the bug id replacement stuff to the config file
#

package ViewHtmlEmail;
use ViewEmail;
@ISA = qw(ViewEmail);
use strict;

#
# Send a simple email on newdir creation
#
sub newDirectory {
    my($self, $model) = @_;

    $self->sendmail($model, "<p>$model->{user} created $model->{newDirectory}</p>");
}

#
# Send a list of affected files and diffs on commit
#
sub commit {
    my($self, $model) = @_;

    # First remove all of the <, >, and \n
    my $log = $self->formatlog($model->{log});

    # Basic header    
    my $text = "<p>$model->{user} committed the following changes on $self->{shortdatetime}.</p>";

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
    foreach my $file (sort keys %{$model->{files}}) {
        my $action = $model->{files}{$file}{action};

        $text .= "   <tr>\n";

        if (defined($self->{cvsweb})) {
            $text .= "      <td><nobr><a href=\"$self->{cvsweb}/$model->{module}/$file\">$file</a>&nbsp;</nobr></td>\n";
        }
        else {
            $text .= "      <td><nobr>$file&nbsp;</nobr></td>\n";
        }

        $text .= "      <td><center>$model->{files}{$file}{rev}</center></td>\n";
        $text .= "      <td><nobr><center>$model->{files}{$file}{delta}</center></nobr></td>\n";
        $text .= "      <td><center>$action</center></td>\n";
        $text .= "   </tr>\n";
    }

    $text .= "</table></p>\n\n";

    # Go through the diffs of the added/modified files
    $text .= "<p>Diffs:</p>\n";
    foreach my $file (sort keys %{$model->{files}}) {
        my $action = $model->{files}{$file}{action};
        if ($action eq "added" || $action eq "modified") {
            my $diff = $model->{files}{$file}{diff};
            $diff = $self->toHtml($diff);

            $text .= "<p><pre>$diff</pre></p>&nbsp<br />\n";
        }
    }

    $text .= "\n\n";

    $self->sendmail($model, $text);
}

#
# Format the log to HTML and handle bug links
#
sub formatlog {
    my($self, $log) = @_;

    $log = $self->SUPER::formatlog($log);
    
    return $self->toHtml($log);
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

1;