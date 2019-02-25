#/usr/bin/env bash

# Pretty print the test descriptions.
function test() {
    echo -e "\n\e[93m\e[1m=== $1 ===\e[0m"
}

# Always fail on error.
set -e

# Log commands except for echo because they are used to explain what is being done.
trap '[[ $BASH_COMMAND != test* ]] && echo -e ">${BASH_COMMAND}"' DEBUG


# WALKTHROUGH STARTS HERE...

test "Print out the version"
encapsia version