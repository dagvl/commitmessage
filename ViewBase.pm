#!/usr/bin/perl -w
#
# ViewBase.pm
# commitmessage Version 1.0
# Copyright 2002 Stephen Haberman
#
# Provides a base implementation for all Views to extend.
#

package ViewBase;
use strict;

#
# Creates a new View object.
#
sub new {
    my($type, $props) = @_;

    my $self = {};
    bless($self, $type);

    return $self;
}

#
# Called after config properties have been set
#
sub init {
    my($self, $model) = @_;
}

#
# Called when a commit occurs
# 
sub commit {
    my($self, $model) = @_;
}

1;