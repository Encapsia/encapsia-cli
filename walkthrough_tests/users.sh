#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1

start_tests

test "List all users"
encapsia users list --all-users

test "List all superusers"
encapsia users list --super-users

test "List all system users"
encapsia users list --system-users

test "Export all users and roles"
encapsia users export /tmp/test_encapsia_users.toml

test "Import users and roles"
encapsia users import /tmp/test_encapsia_users.toml

# Cleanup.
rm /tmp/test_encapsia_users.toml
