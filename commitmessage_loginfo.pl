#!/usr/bin/perl -w
#
# commitmessage_loginfo.pl
# Version 0.9
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
# - MVC-ized the view out to ViewXxx scripts that work off the $om model and
# the commitmessage.config file.
#
# - Removed $LOG_FILE because we assume the entire commit has only
# one message
#
# - Removed $SUMMARY_FILE and instead store diffs in a separate temp file 
# for each added/modified file
#
# The $om structure:
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
# In the View packages, you can loop through the files in the $om structure like:
#
#   foreach my $file (keys %{$om->files}}) {
#      my $action = $om->{files}{$file}{action};
#      ...
#   }
#

use strict;

#
# Constants
#
my $STATE_NONE = 0;
my $STATE_MODIFIED = 1;
my $STATE_ADDED = 2;
my $STATE_REMOVED = 3;
my $STATE_LOG = 4;

my $id = getpgrp();
my $TMPDIR = $ENV{'TMPDIR'} || '/tmp';
my $FILE_PREFIX = "#cvs.$id.";
my $NULL = chr(0);

my $LAST_FILE = "$TMPDIR/${FILE_PREFIX}lastdir";
my $FILES = "$TMPDIR/${FILE_PREFIX}files";

my $CVSROOT = $ENV{'CVSROOT'};


#
# Setup environment
#
umask (002);


#
# Initialize basic variables
#
my $state = $STATE_NONE;
my $user = $ENV{'USER'} || getlogin || (getpwuid($<))[0] || sprintf("uid#%d",$<);
my @files = split(' ', $ARGV[0]);
my @path = split('/', $files[0]);
my $module = $path[0];
my $dir = "";
if ($#path == 0) {
    $dir = "";
} 
else {
    $dir = join('/', @path[1..$#path]) . "/";
}

#
# Initialize the om data structure and callback
# lists.
#
my %om = (
    user => $user,
    module => $module,
    files => {}
 );


#
# Check for a new directory first. This will always appear as a
# single item in the argument list, and an empty log message.
#
if ($ARGV[0] =~ /^(.*) - New directory$/) {
    $om{newdir} = $1;
    
    &cleanup_tmpfiles;

    my @views = &load_views(\%om);
    foreach my $view (@views) {
        $view->newdir(\%om);
    }

    exit 0;
}


#
# Iterate over the body of the message collecting information.
#
my @modified_files;
my @added_files;
my @removed_files;
my @branch_lines;
my @log_lines;
while (<STDIN>) {
    # Drop the newline
    chomp; 
    if (/^Revision\/Branch:/) {
        s,^Revision/Branch:,,;
        push (@branch_lines, split);
        next;
    }
    
    if (/^Modified Files/) { $state = $STATE_MODIFIED; next; }
    if (/^Added Files/) { $state = $STATE_ADDED; next; }
    if (/^Removed Files/) { $state = $STATE_REMOVED; next; }
    if (/^Log Message/) { $state = $STATE_LOG; next; }
    
    s/[ \t\n]+$//; # delete trailing space

    push (@modified_files, split) if ($state == $STATE_MODIFIED);
    push (@added_files, split) if ($state == $STATE_ADDED);
    push (@removed_files, split) if ($state == $STATE_REMOVED);
    push (@log_lines, $_) if ($state == $STATE_LOG);
}

#
# Spit out the information gathered in this pass to 
# the accumlation files.
#
&append_to_file("$FILES", $dir, "modified", @modified_files);
&append_to_file("$FILES", $dir, "added", @added_files);
&append_to_file("$FILES", $dir, "removed", @removed_files);
&append_to_file("$FILES", $dir, "branch", @branch_lines);


#
# Check whether this is the last directory. If not, quit.
#
if (-e "$LAST_FILE") {
    $_ = &read_line("$LAST_FILE");
    my $tmpfiles = $files[0];
    $tmpfiles =~ s,([^a-zA-Z0-9_/]),\\$1,g;
    if (! grep(/$tmpfiles$/, $_)) {
        print "More commits to come...\n";
        exit 0;
    }
}


#
# This is it. The commits are all finished.
#


#
# Strip leading and trailing blank lines from the log message
# since we're actually going to use it this time.
#
while ($#log_lines > -1) {
    last if ($log_lines[0] ne "");
    shift(@log_lines);
}
while ($#log_lines > -1) {
    last if ($log_lines[$#log_lines] ne "");
    pop(@log_lines);
}

$om{log} = join("\n", @log_lines);


#
# Read the filenames saved into the temp files
# into our object model
#
%{$om{files}} = ();
&read_files_to_om(\%om, "$FILES");


#
# We're done getting the file names into the 
# om, so delete the tmpfiles.
#
&cleanup_tmpfiles;


#
# The om has all of the files in, go through 
# so we can read in their specific information.
#
# foreach my $file (keys %{$om{files}}) {
#     print "Got file $file... rev/delta: ";
#     print $om{files}{$file}{rev} . "/" . $om{files}{$file}{delta} . "\n";
# }


#
# Fire the view extension scripts.
#
my @views = &load_views(\%om);
foreach my $view (@views) {
    $view->commit(\%om);
}



#
# Subroutines
#
sub append_to_file {
    my($filename, $dir, $action, @files) = @_;

    open(FILE, ">>$filename") || die("Cannot open file $filename: $!\n");
    foreach my $file (@files) {
        my($rev, $delta, $rcsfile) = &cvs_status("$file");

        my $line = join($NULL, ( "$dir$file", $action, $rev, $delta, $rcsfile ));
        print(FILE "$line\n");
        
        #
        # Only do diffs for modified or added files
        #
        if ($action eq "added" || $action eq "modified") {
            #
            # If this is a binary file, don't try to report a diff; not only is
            # it meaningless, but it also screws up some mailers. We rely on
            # Perl's 'is this binary' algorithm; it's pretty good. But not
            # perfect.
            #
            my $diff = &cvs_diff($file, $rev);

            #
            # Save diff off to tmp file
            #
            my $tmpfile = $dir . $file;
            $tmpfile =~ s,/,-,g;
            open(DIFF, ">$TMPDIR/${FILE_PREFIX}$tmpfile") || die("Couldn't open for write $tmpfile: $_");
            print(DIFF $diff);
            close(DIFF);
        }
    }
    close(FILE);
}

sub read_line {
    my($filename) = @_;
    my($line);

    open(FILE, "<$filename") || die("Cannot open file $filename: $!\n");
    $line = <FILE>;
    close(FILE);
    chomp($line);

    return $line;
}

sub read_files_to_om {
    my($om, $filename) = @_;

    open(FILE, "<$filename");
    while (<FILE>) {
        chomp;
        my $line = $_;
        my @mary = split(/$NULL/, $_);
        my $file = $mary[0];

        # Save the file into the om
        %{$om{files}{$file}} = ();
        $om{files}{$file}{action} = $mary[1];
        $om{files}{$file}{rev} = $mary[2];
        $om{files}{$file}{prev_rev} = &calc_prev_rev($mary[2]);
        $om{files}{$file}{delta} = $mary[3];
        $om{files}{$file}{rcsfile} = $mary[4];

        # Check for a diff 
        my $action = $mary[1];
        if ($action eq "added" || $action eq "modified") {
            my $diff = "";
            my $tmpfile = $file;
            $tmpfile =~ s,/,-,g;

            open(DIFF, "<$TMPDIR/${FILE_PREFIX}$tmpfile") || die("Couldn't open for read $tmpfile: $_");
            while(<DIFF>) {
                $diff .= $_;
            }
            close(DIFF);

            $om{files}{$file}{diff} = $diff;
        }
    }
    close(FILE);
}

sub cleanup_tmpfiles {
    my(@files);

    opendir(DIR, $TMPDIR);
    push(@files, grep(/^${FILE_PREFIX}/, readdir(DIR)));
    closedir(DIR);
    foreach (@files) {
        unlink "$TMPDIR/$_";
    }
}

sub cvs_status {
    my($file) = @_;

    my $rev = "";
    my $delta = "";
    my $rcsfile = "";

    open(RCS, "-|") || exec 'cvs', '-Qn', 'status', $file;
    while (<RCS>) {
        if (/^[ \t]*Repository revision/) {
            chomp;
            my @revline = split(' ', $_);
            $rev = $revline[2];
            $rcsfile = $revline[3];
            $rcsfile =~ s,^$CVSROOT/,,;
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

sub cvs_diff {
    my($file, $rev) = @_;

    my $diff = "";

    if (($file =~ /\.(?:pdf|gif|jpg|mpg)$/i) || (-B $file)) {
        $diff .= "<<Binary file>>";
    }
    else {
        #
        # Get the differences between this and the previous revision,
        # being aware that new files always have revision '1.1' and
        # new branches always end in '.n.1'.
        #
        my $prev_rev = &calc_prev_rev($rev);

        if ($rev eq '1.1') {
            open(DIFF, "-|") || exec 'cvs', '-Qn', 'update', '-p', '-r1.1', $file;
            $diff .= "Index: $file\n=================================="
                . "=================================\n";
        }
        else {
            open(DIFF, "-|") 
                || exec 'cvs', '-Qn', 'diff', '-u', "-r$prev_rev", "-r$rev", $file;
        }

        while (<DIFF>) {
            $diff .= $_;
        }

        close(DIFF);
    }

    return $diff;
}

#
# Get the previous revision
#
sub calc_prev_rev {
    my($rev) = @_;
    my $prev_rev = "";

    if ($rev =~ /^(.*)\.([0-9]+)$/) {
        my $prev = $2 - 1;
        $prev_rev = $1 . '.' . $prev;

        # Truncate if first rev on branch
        $prev_rev =~ s/\.[0-9]+\.0$//;
    }

    return $prev_rev;
}

#
# Invoke any scripts that match the prefixes so
# that they can plug into the views variable.
#
sub load_views {
    my($om) = @_;

    my $EQUALS = " *= *";
    my $VIEW_NAME = "[a-zA-Z0-9_]+";
    my $PACKAGE_NAME = "[^\n]+";
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

        # Import the library and call new on it, passing in the props
        my $foo = "use lib '$CVSROOT/CVSROOT';";
        $foo .= "use $views{$name}{commitmessagePackage};";
        $foo .= "\$viewObject = $views{$name}{commitmessagePackage}->new(\$views{$name}, \\%om);";

        eval($foo) || die "An error occurred: $@\n";

        push(@viewObjects, $viewObject);
    }

    return @viewObjects;
}