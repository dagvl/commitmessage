#!/usr/bin/perl -w
#
# Model.pm
# commitmessage Version 1.0-alpha1
#
# Wraps the module that gets sent between
# the Controller and Views.
#

package Controller;
use CvsUtil;
use Model;
use strict;

#
# Setup environment
#
umask (002);

#
# Constants
#

my $id = getpgrp();
my $FILE_PREFIX = "#cvs.$id.";
my $TMPDIR = $ENV{'TMPDIR'} || '/tmp';
my $LAST_FILE = "$TMPDIR/${FILE_PREFIX}lastdir";
my $FILES = "$TMPDIR/${FILE_PREFIX}files";

sub NULL {
    return chr(0);
}

sub CVSROOT {
    return $ENV{CVSROOT};
}

#
# Creates a new Controller object
#
# Params: the params from CVS
#
#   In loginfo, option %s
#   directory-relative-to-CVSROOT file-1 file-2 ...
#
sub new {
    my($type) = @_;

    my $self = {};
    bless($self, $type);

    return $self;
}

#
# Parses the %{s} ARGV sent to loginfo.pl to create the
# model and check for new directory commits.
#
sub parseArgv {
    my($self, @argv) = @_;

    # Pull the module name off of the commitDirectory to get the currentDirectory.
    my($currentDirectoryWithModule, @files) = split(' ', $argv[0]);
    my @directoryPath = split('/', $currentDirectoryWithModule);
    my $module = $directoryPath[0];

    # Handle for having no / if the commit is in the root dir of the module
    if ($#directoryPath == 0) {
        $self->{currentDirectory} = "";
    } 
    else {
        $self->{currentDirectory} = join('/', @directoryPath[1..$#directoryPath]) . "/";
    }

    # Save the path with the module in it for the $LAST_FILE check
    $self->{currentDirectoryWithModule} = $currentDirectoryWithModule;

    my $user = $ENV{'USER'} || getlogin || (getpwuid($<))[0] || sprintf("uid#%d",$<);
    $self->model(Model->new($user, $module));

    # Check for - New Directory
    if ($#argv == 4 && $argv[1] eq "-" && $argv[2] eq "New" && $argv[3] eq "Directory") {
        $self->model->newDirectory($self->{currentDirectory});
    }
}

#
# The model the Controller is working with
#
sub model {
    my $self = shift;
    if (@_) {
        $self->{model} = shift;
    }
    return $self->{model};
}

#
# The views for the Controller has loaded
#
sub views {
    my $self = shift;
    return $self->{views};
}

#
# Runs the main logic flow
#
sub main {
    my($self) = @_;

    # See if this commit is just a new directory commit
    if (defined($self->model->newDirectory)) {
        $self->cleanupTempFiles;

        $self->loadViews;
        $self->execNewDirectory;

        return;
    }

    # Save the files in the current directory to the persistent log
    $self->saveCurrentFilesToPersistentLog;

    if (!$self->isLastDirectoryOfCommit) {
        print "More commits to come...\n";
        return;
    }

    $self->parseAndSaveLogMessage;

    # Read in all of the filenames saved into the temp files into the model
    $self->model->importPersistedLog("$FILES");

    $self->cleanupTempFiles;

    $self->loadViews;
    $self->execCommit;
}

#
# Return whether this loginfo is in the last dir of the commit
#
sub isLastDirectoryOfCommit {
    my($self) = @_;

    if (-e "$LAST_FILE") {
        my $lastDir = $self->readFirstLine("$LAST_FILE");
        my $fullPath = Controller->CVSROOT . "/" . $self->{currentDirectoryWithModule};
        if ($fullPath eq $lastDir) {
            return 1;
        }
    }
    return 0;
}

#
#
# Iterate over the body of the message (STDIN) collecting information
#
sub saveCurrentFilesToPersistentLog {
    my($self)= @_;

    my $STATE_NONE = 0;
    my $STATE_MODIFIED = 1;
    my $STATE_ADDED = 2;
    my $STATE_REMOVED = 3;
    my $STATE_LOG = 4;

    my $state = $STATE_NONE;

    my @modified_files = ();
    my @added_files = ();
    my @removed_files = ();
    my @branch_lines = ();
    my @log_lines = ();
    while (<STDIN>) {
        # Drop the newline
        chomp; 
        if (/^Revision\/Branch:/) {
            s,^Revision/Branch:,,;
            push (@branch_lines, split);
            next;
        }
        
        if (/^Modified Files/) { $state = $STATE_MODIFIED; next; }
        if (/^Added Files/) { $state= $STATE_ADDED; next; }
        if (/^Removed Files/) { $state = $STATE_REMOVED; next; }
        if (/^Log Message/) { $state = $STATE_LOG; next; }
        
        s/[ \t\n]+$//; # delete trailing space

        push (@modified_files, split) if ($state == $STATE_MODIFIED);
        push (@added_files, split) if ($state == $STATE_ADDED);
        push (@removed_files, split) if ($state == $STATE_REMOVED);
        push (@log_lines, $_) if ($state == $STATE_LOG);
    }

    # Save the @log_lines for parseAndSaveLogMessage
    $self->{log_lines} = \@log_lines;

    #
    # Spit out the information gathered in this pass to 
    # the accumlation files.
    #
    $self->appendFiles("modified", @modified_files);
    $self->appendFiles("added", @added_files);
    $self->appendFiles("removed", @removed_files);
    $self->appendFiles("branch", @branch_lines);
}

#
# Parses the log_lines saved in self and sets log in the model.
#
sub parseAndSaveLogMessage {
    my($self) = @_;

    my @log_lines = @{$self->{log_lines}};

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

    $self->model->log(join("\n", @log_lines));
}

#
# Invoke any scripts that match the prefixes so
# that they can plug into the views variable.
#
sub loadViews {
    my($self) = @_;

    my $EQUALS = " *= *";
    my $VIEW_NAME = "[a-zA-Z0-9_]+";
    my $PACKAGE_NAME = "[^\n]*";
    my $PROPERTY_NAME = "[a-zA-Z0-9_]+";
    my $PROPERTY_VALUE = "[^\n]*";
    my $PROPERTY_EQUALS = " *((=>)|(=)) *";
    
    # Read in the entire config file
    my @config = ();
    open(FILE, Controller->CVSROOT . "/CVSROOT/commitmessage/config");
    while(<FILE>) {
        chomp;
        push(@config, $_);
    }
    close(FILE);

    # Find any views for this specific module

    my %views = ();
    my $module = $self->model->module;

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
        if ($line =~ /^ALL.($VIEW_NAME)\.($PROPERTY_NAME)$PROPERTY_EQUALS($PROPERTY_VALUE)$/) {
##            print "Set global $1.$2 = " . Controller->optionalEval($6, $3, $self->model) . "\n";
            $views{$1}{$2} = Controller->optionalEval($6, $3, $self->model->om);
        }
    }

    # Now override defaults and fill in module-specific properties
    foreach my $line (@config) {
        if ($line =~ /^$module\.($VIEW_NAME)\.($PROPERTY_NAME)$PROPERTY_EQUALS($PROPERTY_VALUE)$/) {
##            print "Set module $1.$2 = " . Controller->optionalEval($6, $3, $self->model) . "\n";
            $views{$1}{$2} = Controller->optionalEval($6, $3, $self->model->om);
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
        my $foo .= "use $views{$name}{commitmessagePackage};";
        $foo .= "\$viewObject = $views{$name}{commitmessagePackage}->new();";
        eval($foo) || die "An error occurred: $@\n";

        foreach my $prop (keys %{$views{$name}}) {
##            print "Setting $prop = $views{$name}{$prop}\n";
            $viewObject->{$prop} = $views{$name}{$prop};
        }

        $viewObject->init($self->model->om);

        push(@viewObjects, $viewObject);
    }

    $self->{views} = \@viewObjects;
}

#
# Eval the property if => is used
# 
# Params: value, = or =>, model to use if evaling
sub optionalEval {
    my($type, $value, $assignment, $model) = @_;
    if ($assignment eq "=>") {
        return eval("\"$value\"");
    }
    else {
        return $value;
    }
}

#
# Appends the files of the given type to the temp file.
#
sub appendFiles {
    my($self, $action, @files) = @_;

    open(FILE, ">>$FILES") || die("Cannot open file $FILES: $!\n");
    foreach my $file (@files) {
        my($rev, $delta, $rcsfile) = CvsUtil->status("$file");

        my $line = join(Controller->NULL, ("$self->{currentDirectory}$file", $action, $rev, $delta, $rcsfile ));
        print(FILE "$line\n");
        
        #
        # Only do diffs for modified or added files
        #
        if ($action eq "added" || $action eq "modified") {
            my $diff = CvsUtil->diff($file, $rev);

            #
            # Save diff off to tmp file
            #
            my $relativeFilePath = "$self->{currentDirectory}$file";
            my $tmpFile = Controller->getTempFileFullPath($relativeFilePath);
            open(DIFF, ">$tmpFile") || die("Couldn't open for write $tmpFile: $_");
            print(DIFF $diff);
            close(DIFF);
        }
    }
    close(FILE);
}

#
# Reads the first line of a file
#
# Params: filename
#
sub readFirstLine {
    my($self, $filename) = @_;

    open(FILE, "<$filename") || die("Cannot open file $filename: $!\n");
    my $line = <FILE>;
    close(FILE);
    chomp($line);

    return $line;
}

#
# Removes the temp files used by the Controller
#
sub cleanupTempFiles {
    my($self) = @_;

    my(@files);
    opendir(DIR, $TMPDIR);
    push(@files, grep(/^${FILE_PREFIX}/, readdir(DIR)));
    closedir(DIR);
    foreach (@files) {
        unlink "$TMPDIR/$_";
    }
}

#
# Executes the newDirectory method on each View
#
sub execNewDirectory {
    my($self) = @_;

    my @views = @{$self->views};
    foreach my $view (@views) {
        $view->newDirectory($self->model->om);
    }
}

#
# Executes the commit method on each View
#
sub execCommit {
    my($self) = @_;

    my @views = @{$self->views};
    foreach my $view (@views) {
        $view->commit($self->model->om);
    }
}

#
# Return the file to store diffs in
#
# Params: filename
#
sub getTempFileFullPath {
    my($type, $file) = @_;
    $file =~ s,/,-,g;
    return "$TMPDIR/${FILE_PREFIX}$file";
}

1;