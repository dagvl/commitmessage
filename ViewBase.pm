#!/usr/bin/perl -w
#
# ViewBase.pm
# Version 0.9
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
# Called when a new directory commit occurs
#
sub newDirectory {
    my($self, $model) = @_;

}

#
# Called when a regular commit occurs
# 
sub commit {
    my($self, $model) = @_;
}

1;