#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Print out overall help"
encapsia help

test "Print out help on help"
encapsia help help

test "Print out help on users"
encapsia help users