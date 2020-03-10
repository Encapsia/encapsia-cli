#!/usr/bin/env bash

# Force colour always, even when redirecting to a file.
export ENCAPSIA_COLOUR=always

# Load "library" code
source $(dirname "$0")/lib.sh

banner "Starting walkthrough tests of encapsia-cli"
echo "These are *not* self-verifying tests, so check the output for reasonableness!"

THIS_DIR=$(dirname "$0")
bash $THIS_DIR/help.sh "$@"
bash $THIS_DIR/version.sh "$@"
bash $THIS_DIR/token.sh "$@"
bash $THIS_DIR/config.sh "$@"
bash $THIS_DIR/plugins.sh "$@"
bash $THIS_DIR/database.sh "$@"
bash $THIS_DIR/fixtures.sh "$@"
bash $THIS_DIR/run.sh "$@"
bash $THIS_DIR/users.sh "$@"
# NB No walkthrough tests for httpie because it is interactive
# NB No walkthrough tests for shell because it is interactive

banner "End of tests"