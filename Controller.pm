#!/usr/bin/perl -w
#
# Model.pm
# commitmessage Version 1.0-beta1
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

    # Pull the module name off of the commitDirectory to get the rootDirectory.
    my($currentDirectoryWithRoot, @files) = split(' ', $argv[0]);
    my @directoryPath = split('/', $currentDirectoryWithRoot);

    # Handle for having no / if the commit is in the root dir of the module, so that
    # we can always go $self->{currentDirectoryWithSlash}$file and not worry about a 
    # / being between the two or not.
    my $rootDirectory;
    if ($#directoryPath < 0) {
        # Then the directory was really a file and we're in the rootDirectory
        $rootDirectory = "";
        $self->{currentDirectory} = "";
        $self->{currentDirectoryWithSlash} = "";
    } 
    else {
        $rootDirectory = $directoryPath[0];
        $self->{currentDirectory} = join('/', @directoryPath[0..$#directoryPath]);
        $self->{currentDirectoryWithSlash} = $self->{currentDirectory} . "/";
    }

    my $user = $ENV{'USER'} || getlogin || (getpwuid($<))[0] || sprintf("uid#%d",$<);
    $self->model(Model->new($user));
    $self->model->rootDirectory($rootDirectory);

    # Check for - New Directory
    if ($#files == 2 && $files[0] eq "-" && $files[1] eq "New" && $files[2] eq "directory") {
        $self->model->addDirectory($self->{currentDirectory});
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
    my $self = shift;

    # Make sure this commit is not just a new directory commit
    if ($self->model->directoriesCount != 1) {

        # Save the files in the current directory to the persistent log
        $self->saveCurrentFilesToPersistentLog;

        my $isImport = 0;
        if ($self->couldBeImport) {
            # Check the log for the definitive answer
            $self->parseAndSaveLogMessage;

            if ($self->isImport) {
                $self->model->baseDirectory("CVSROOT");
                $self->parseImportLog;

                # Flag to go straight to cleanup/load/commit
                $isImport = 1;
            }
        }

        # Make sure an import hasn't occurred
        if ($isImport == 0) {
            # Could be a multi-directory commit
            if (!$self->isLastDirectoryOfCommit) {
                print "More commits to come...\n";
                return;
            }

            # This was the last directory, get the log
            $self->parseAndSaveLogMessage;
            # Read in all of the filenames saved into the temp files into the model
            $self->importPersistedLog("$FILES");
        }
    }

    $self->model->calculateBaseDirectory;
    $self->cleanupTempFiles;
    $self->loadViews;
    $self->commit;
}

#
# Return whether this loginfo could be the result of an import command
#
sub couldBeImport {
    my $self = shift;

    if (-e "$LAST_FILE") {
        return 0;
    }
    else {
        return 1;
    }
}

#
# Return whether this loginfo was the result of an import command
#
sub isImport {
    my $self = shift;

    my $log = $self->model->log;
    if ($log =~ /Status:\n\nVendor Tag:\t/) {
        return 1;
    }

    return 0;
}

#
# Parses the special log sent in with an import command
# and puts the file information into the Model.
#
sub parseImportLog {
    my $self = shift;

    my $log = $self->model->log;
    my @mary = split("Status:\n\nVendor Tag:\t", $log);

    $self->model->log($mary[0]);

    @mary = split("\n", $mary[1]);
    foreach my $line (@mary) {
        if ($line =~ /^N /) {
            my $file = substr($line, 2);
            my($delta, $rcsfile, $diff) = ("+", Controller->CVSROOT . $file, "<<new file>>");
            $self->model->addFile($file, "added", 1.1, $delta, $rcsfile, $diff);
        }
    }
}

#
# Return whether this loginfo is in the last dir of the commit
#
sub isLastDirectoryOfCommit {
    my $self = shift;

    if (-e "$LAST_FILE") {
        my $lastDir = $self->readFirstLine("$LAST_FILE");
        my $fullPath = Controller->CVSROOT . "/" . $self->{currentDirectory};
##        print "lastDir = $lastDir\n";
##        print "fullPath = $fullPath\n";
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
    my $self= shift;

    my $STATE_NONE = 0;
    my $STATE_MODIFIED = 1;
    my $STATE_ADDED = 2;
    my $STATE_REMOVED = 3;
    my $STATE_LOG = 4;
    my $STATE_IMPORT = 5;

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
    my $self = shift;

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
    my $self = shift;

    my $EQUALS = " *= *";
    my $MATCH_NAME = "[a-zA-Z0-9_-]+";
    my $VIEW_NAME = "[a-zA-Z0-9_-]+";
    my $PACKAGE_NAME = "[^\n]*";
    my $PROPERTY_NAME = "[a-zA-Z0-9_-]+";
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

    # Find any views for this specific commit

    # A hash to map views to their settings
    my %views = ();

    # A hash to map matches to their regex's
    my %matches = ();
    $matches{DEFAULT} = ".*";

    # Module is no longer used, so match against the baseDirectory
    my $basedir = $self->model->baseDirectory;

    # Look for match definitions
    foreach my $line (@config) {
        if ($line =~ /^($MATCH_NAME)$EQUALS($PROPERTY_VALUE)$/) {
            my $switch = 0;
            my $eval = "if (\$basedir =~ /$2/) { \$switch = 1; }";
##            print "Evaling: $eval\n";
            eval($eval);
            if ($switch == 1) {
##                print "Added match $1\n";
                $matches{$1} = 1;
            }
            else {
##                print "Ignored match $1\n";
            }
        }
    }

    # Now that we have the matches, look for view
    # definitions for all of the found matches
    foreach my $line (@config) {
        if ($line =~ /^($MATCH_NAME)\.($VIEW_NAME)$EQUALS($PACKAGE_NAME)$/) {
            # Found a View definition, make sure the match exists
            if (exists $matches{$1}) {
                %{$views{$2}} = ();

                $views{$2}{commitmessageName} = $2;
                $views{$2}{commitmessagePackage} = $3;
            }
        }
        # Look for the view definition
        elsif ($line =~ /^($MATCH_NAME)\.($VIEW_NAME)\.($PROPERTY_NAME)$PROPERTY_EQUALS($PROPERTY_VALUE)$/) {
            # Make sure the match is valid
            if (exists $matches{$1}) {
                $views{$2}{$3} = Controller->optionalEval($7, $4, $self->model);
            }
        }

    }

    # Now convert the views to objects
    my @viewObjects = ();
    foreach my $name (keys %views) {
        my $viewObject = "";

##        print "Executing view $name\n";

        # Allow the global package definition to be ignored by a match one
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

        $viewObject->init($self->model);

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

        my $line = join(Controller->NULL, ("$self->{currentDirectoryWithSlash}$file", $action, $rev, $delta, $rcsfile ));
        print(FILE "$line\n");
        
        #
        # Only do diffs for modified or added files
        #
        if ($action eq "added" || $action eq "modified") {
            my $diff = CvsUtil->diff($file, $rev);

            #
            # Save diff off to tmp file
            #
            my $relativeFilePath = "$self->{currentDirectoryWithSlash}$file";
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
    my $self = shift;

    my(@files);
    opendir(DIR, $TMPDIR);
    push(@files, grep(/^${FILE_PREFIX}/, readdir(DIR)));
    closedir(DIR);
    foreach (@files) {
        unlink "$TMPDIR/$_";
    }
}

#
# Executes the commit method on each View
#
sub commit {
    my $self = shift;

    my @views = @{$self->views};
    foreach my $view (@views) {
        $view->commit($self->model);
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

#
# Read a file into the model
#
# Params: filename
#
sub importPersistedLog {
    my($self, $filename) = @_;

    open(FILE, "<$filename");
    while (<FILE>) {
        chomp;
        my $line = $_;
        my $null = Controller->NULL;
        my @mary = split(/$null/, $_);

        my $file = $mary[0];
        my $action = $mary[1];
        my $diff = "";

        # Check for a diff 
        if ($action eq "added" || $action eq "modified") {
            my $tmpFile = Controller->getTempFileFullPath($file);
            open(DIFF, "<$tmpFile") || die("Couldn't open for read $tmpFile: $_");
            while(<DIFF>) {
                $diff .= $_;
            }
            close(DIFF);
        }

        $self->model->addFile(
            $file,
            $action,
            $mary[2],
            $mary[3],
            $mary[4],
            $diff);
    }
    close(FILE);
}

1;