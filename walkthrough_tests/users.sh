#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1

start_tests

test "Add superuser"
encapsia users add-superuser tcorbettclark@cmedtechnology.com Timothy Corbett-Clark

test "List all superusers"
encapsia users list --super-users

test "Delete superuser"
encapsia users delete tcorbettclark@cmedtechnology.com


test "Add system user"
encapsia users add-systemuser a-description cap1,cap2,cap3

test "List all system users"
encapsia users list --system-users

test "Delete system user"
encapsia users delete system@a-description.encapsia.com


test "List all users"
encapsia users list --all-users


test "Export all users and roles"
encapsia users export /tmp/test_encapsia_users.toml
cat /tmp/test_encapsia_users.toml

test "Import users and roles"
encapsia users import /tmp/test_encapsia_users.toml

# Cleanup.
rm /tmp/test_encapsia_users.toml
