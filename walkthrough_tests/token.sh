#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Get whoami info about current token"
encapsia token whoami

test "Extend lifespan of token (changes the encapsia credentials)"
encapsia token extend
encapsia token whoami

# Don't normally run the following because it is too distructive!
# test "Expire current token"
# encapsia token expire