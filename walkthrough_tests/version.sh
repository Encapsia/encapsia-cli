#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Print out the version"
encapsia version
