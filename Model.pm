#!/usr/bin/perl -w
#
# Model.pm
# commitmessage Version 1.0-alpha1
#
# Wraps the module that gets sent between
# the Controller and Views.
#

package Model;
use Controller;
use CvsUtil;
use strict;

#
# Creates a new Model object.
#
# Params: user, module
#
sub new {
    my($type, $user, $module) = @_;

    my $self = {};
    bless($self, $type);

    $self->{om} = {};
    $self->om->{user} = $user;
    $self->om->{module} = $module;
    $self->om->{files} = {};

    return $self;
}

#
# Returns the internal, non-blessed hash
#
sub om {
    my($self) = @_;
    return $self->{om};
}

#
# The user for the commit
#
sub user {
    my($self) = @_;
    return $self->om->{user};
}

#
# The module the commit happened in
#
sub module {
    my $self = shift;
    if(@_) {
        $self->om->{module} = shift;
    }
    return $self->om->{module};
}

#
# The log for the commit
#
sub log {
    my $self = shift;
    if(@_) {
        $self->om->{log} = shift;
    }
    return $self->om->{log};
}

#
# The new directory created by the commit, assuming
# there is one
#
sub newDirectory {
    my $self = shift;
    if(@_) {
        $self->om->{newDirectory} = shift;
    }
    return $self->om->{newDirectory};
}

#
# Return the list of files
#
sub files {
    my $self = shift;
    return $self->om->{files};
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

        $self->addEntry(
            $file,
            $action,
            $mary[2],
            $mary[3],
            $mary[4],
            $diff);
    }
    close(FILE);
}

#
# Add a file to the model
#
# Params: file, action, rev, delta, rcsfile, diff
#
sub addEntry {
    my($self, $file, $action, $rev, $delta, $rcsfile, $diff) = @_;

    # Save the file into the model
    %{$self->om->{files}{$file}} = ();

    $self->om->{files}{$file}{action} = $action;
    $self->om->{files}{$file}{rev} = $rev;
    $self->om->{files}{$file}{prev} = CvsUtil->calculatePreviousRevision($rev);
    $self->om->{files}{$file}{delta} = $delta;
    $self->om->{files}{$file}{rcsfile} = $rcsfile;
    $self->om->{files}{$file}{diff} = $diff;
}

1;