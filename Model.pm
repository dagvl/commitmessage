#!/usr/bin/perl -w
#
# Model.pm
# commitmessage Version 1.0
# Copyright 2002 Stephen Haberman
#
# Wraps the model that gets sent between
# the Controller and Views.
#

package Model;
use Controller;
use CvsUtil;
use strict;

#
# Creates a new Model object.
#
# Params: user
#
sub new {
    my($type, $user) = @_;

    my $self = {};
    bless($self, $type);

    $self->{user} = $user;
    $self->{files} = {};
    $self->{directories} = {};
    $self->{indirectlyAffectedDirectories} = {};

    return $self;
}

#
# The user for the commit
#
sub user {
    my $self = shift;
    return $self->{user};
}

#
# The root directory the commit happened in
#
sub rootDirectory {
    my $self = shift;
    if (@_) {
        $self->{rootDirectory} = shift;
    }
    return $self->{rootDirectory};
}

#
# The base directory the commit happened
# in (the greatest common ancestor of each element).
#
sub baseDirectory {
    my $self = shift;
    if (@_) {
        $self->{baseDirectory} = shift;
    }
    return $self->{baseDirectory};
}

#
# The log for the commit
#
sub log {
    my $self = shift;
    if (@_) {
        $self->{log} = shift;
    }
    return $self->{log};
}

#
# Return the hash of file names to stats
#
sub files {
    my $self = shift;
    return $self->{files};
}

#
# Return the hash of directory names to stats
#
sub directories {
    my $self = shift;
    return $self->{directories};
}

#
# Return the number of files
#
sub filesCount {
    my $self = shift;
    return scalar keys %{$self->{files}};
}

#
# Return the number of directories
#
sub directoriesCount {
    my $self = shift;
    return scalar keys %{$self->{directories}};
}

#
# Return the sorted list of file names
# 
sub fileKeysSorted {
    my $self = shift;
    return sort keys %{$self->{files}};
}

#
# Return the sorted list of directory names
#
sub directoryKeysSorted {
    my $self = shift;
    return sort keys %{$self->{directories}};
}

#
# Return the sorted list of indirectly affected directory names
#
sub indirectlyAffectedDirectoryKeysSorted {
    my $self = shift;
    return sort keys %{$self->{indirectlyAffectedDirectories}};
}

#
# Any directories directly affected by the commit.
#
# Params: directory, action, movedTo (optional)
#
sub addDirectory {
    my($self, $directory, $action, $movedTo) = @_;

    # Save the directory into the model
    %{$self->{directories}{$directory}} = ();

    $self->{directories}{$directory}{action} = $action;

    if ($action eq "moved") {
        $self->{directories}{$directory}{movedTo} = $movedTo;
    }
}

#
# Add a file to the model
#
# Params: file, action, rev, delta, rcsfile, diff, movedTo (optional)
#
sub addFile {
    my($self, $file, $action, $rev, $delta, $rcsfile, $diff, $movedTo) = @_;

    # Get the file's directory
    my @dirs = split('/', $file);
    my $dir = join('/', @dirs[0..($#dirs - 1)]);
    if (not exists $self->{indirectlyAffectedDirectories}{$dir}) {
        %{$self->{indirectlyAffectedDirectories}{$dir}} = ();
    }
    $self->{indirectlyAffectedDirectories}{$dir}++;

    # Save the file into the model
    %{$self->{files}{$file}} = ();

    $self->{files}{$file}{action} = $action;
    $self->{files}{$file}{rev} = $rev;
    $self->{files}{$file}{prev} = CvsUtil->calculatePreviousRevision($rev);
    $self->{files}{$file}{delta} = $delta;
    $self->{files}{$file}{rcsfile} = $rcsfile;
    $self->{files}{$file}{diff} = $diff;

    if ($action eq "moved") {
        $self->{files}{$file}{movedTo} = $movedTo;
    }
}

#
# Goes through the directories and files and finds the base 
# directory (the greatest common ancestor).
#
sub calculateBaseDirectory {
    my $self = shift;

    # Assume the base dir is the first one and then cut it down
    my $basedir;
    if ($self->directoriesCount > 0) {
        $basedir = ($self->directoryKeysSorted)[0];
    }
    else {
        $basedir = ($self->indirectlyAffectedDirectoryKeysSorted)[0];
    }

##    print "Basedir is initially $basedir\n";

    my @basedirArray = split('/', $basedir);

    foreach my $dir ($self->indirectlyAffectedDirectoryKeysSorted) {
##        print "Comparing basedir with $dir\n";
        @basedirArray = $self->greatestCommonDirectory($dir, @basedirArray);
##        print "Now basedir " . join('/', @basedirArray) . "\n";
    }
    foreach my $dir ($self->directoryKeysSorted) {
##        print "Comparing basedir with $dir\n";
        @basedirArray = $self->greatestCommonDirectory($dir, @basedirArray);
##        print "Now basedir " . join('/', @basedirArray) . "\n";
    }

##    print "Basedir is finally " . join('/', @basedirArray) . "\n";
    $basedir = join('/', @basedirArray);
    $self->baseDirectory($basedir);
}

#
# Walks through two directories and returns the greatest
# common sub directory.
#
# Params: dir2, dir1Array
# Return: the new dirArray
#
sub greatestCommonDirectory {
    my($self, $dir2, @dir1Array) = @_;

    my @gcdArray = ();
    my @dir2Array = split('/', $dir2);
    my $i = 0;
    while ($i <= $#dir1Array && $i <= $#dir2Array) {
        if ($dir1Array[$i] eq $dir2Array[$i]) {
            push(@gcdArray, $dir1Array[$i]);
            $i++;
        }
        else {
            last;
        }
    }

    @gcdArray;
}

1;