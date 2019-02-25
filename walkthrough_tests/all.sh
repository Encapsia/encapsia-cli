#!/usr/bin/env bash

echo "Exercise encapsia commands."
echo "These are *not* self-verifying tests, so check the output for reasonableness!"

THIS_DIR=$(dirname "$0")
bash $THIS_DIR/help.sh "$@"
bash $THIS_DIR/version.sh "$@"
bash $THIS_DIR/token.sh "$@"
bash $THIS_DIR/config.sh "$@"
bash $THIS_DIR/plugins.sh "$@"
bash $THIS_DIR/database.sh "$@"
bash $THIS_DIR/fixtures.sh "$@"
# NB No walkthrough tests for httpie because it is interactive
# NB No walkthrough tests for shell because it is interactive