#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1

start_tests

test "Create a fixture"
encapsia fixtures create test_fixture

test "Use a fixture"
encapsia fixtures use --yes test_fixture
sleep 5

test "Delete a fixture"
encapsia fixtures delete --yes test_fixture

test "List all fixtures"
encapsia fixtures list