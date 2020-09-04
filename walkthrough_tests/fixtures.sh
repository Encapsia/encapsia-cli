#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Create a fixture"
encapsia fixtures create test_fixture

# Don't test using a fixture because too disruptive of target server
test "Use a fixture (DISABLED: to be less invasive on test server)"
# encapsia fixtures use --yes test_fixture
# sleep 5

test "Delete a fixture"
encapsia fixtures delete --yes test_fixture

test "List all fixtures"
encapsia fixtures list