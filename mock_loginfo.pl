#!/usr/bin/perl -w
#
# mock_loginfo.pl
# commitmessage Version 0.91
#
# This script will test a commitmessage installation by mimicking the
# functionality of commitmessage_loginfo.pl and executing the
# configured Views for a repository.
#
# Usage:
#
#   mock_loginfo.pl module [View]
#
# The commitmessage.config will then be read and a mock $om
# data structure will be passed to the various Views.
#

use strict;

#
# Initialize the om data structure and callback
# lists.
#
my %om = (
    user => "testUser",
    module => $ARGV[1],
    files => {}
 );


# Save the file into the om
my $file = "$om{module}/file.txt";
%{$om{files}{$file}} = ();
$om{files}{$file}{action} = "added";
$om{files}{$file}{rev} = "1.1";
$om{files}{$file}{prev_rev} = "0";
$om{files}{$file}{delta} = "+1-5";
$om{files}{$file}{rcsfile} = "/long/path/$file";
$om{files}{$file}{diff} = $diff;

#
# Invoke any scripts that match the prefixes so
# that they can plug into the views variable.
#
sub load_views {
    my($om) = @_;

    my $EQUALS = " *= *";
    my $VIEW_NAME = "[a-zA-Z0-9_]+";
    my $PACKAGE_NAME = "[^\n]*";
    my $PROPERTY_NAME = "[a-zA-Z0-9_]+";
    my $PROPERTY_VALUE = "[^\n]*";
    
    # Read in the entire config file
    my @config = ();
    open(FILE, "$CVSROOT/CVSROOT/commitmessage.config");
    while(<FILE>) {
        chomp;
        push(@config, $_);
    }
    close(FILE);

    # Find any views for this specific module

    my %views = ();

    # Look for view definitions
    foreach my $line (@config) {
        # Look for global definitions
        if ($line =~ /^ALL\.($VIEW_NAME)$EQUALS($PACKAGE_NAME)$/) {
##            print "Found global view $1 = $2\n";
            %{$views{$1}} = ();
            $views{$1}{commitmessageName} = $1;
            $views{$1}{commitmessagePackage} = $2;
        }
        # Look for module definitions
        if ($line =~ /^$module\.($VIEW_NAME)$EQUALS($PACKAGE_NAME)$/) {
##            print "Found module view $1 = $2\n";
            %{$views{$1}} = ();
            $views{$1}{commitmessageName} = $1;
            $views{$1}{commitmessagePackage} = $2;
        }
    }

    # Fill in global defaults
    foreach my $line (@config) {
        if ($line =~ /^ALL.($VIEW_NAME)\.($PROPERTY_NAME)$EQUALS($PROPERTY_VALUE)$/) {
##            print "Set global $1.$2 = $3\n";
            $views{$1}{$2} = $3;
        }
    }

    # Now override defaults and fill in module-specific properties
    foreach my $line (@config) {
        if ($line =~ /^$module\.($VIEW_NAME)\.($PROPERTY_NAME)$EQUALS($PROPERTY_VALUE)$/) {
##            print "Set module $1.$2 = $3\n";
            $views{$1}{$2} = $3;
        }
    }

    # Now convert the views to objects
    my @viewObjects = ();
    foreach my $name (keys %views) {
        my $viewObject = "";

        # Allow the global package definition to be ignored by a module one
        if ($views{$name}{commitmessagePackage} eq "") {
##            print "Skipping $name...\n";
            next;
        }

        # Import the library and call new on it, passing in the props
        my $foo = "use lib '$CVSROOT/CVSROOT';";
        $foo .= "use $views{$name}{commitmessagePackage};";
        $foo .= "\$viewObject = $views{$name}{commitmessagePackage}->new(\$views{$name}, \\%om);";

        eval($foo) || die "An error occurred: $@\n";

        push(@viewObjects, $viewObject);
    }

    return @viewObjects;
}