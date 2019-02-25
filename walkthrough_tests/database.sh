#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1

start_tests

test "Create a backup"
encapsia database backup /tmp/test_encapsia_backup
ls -l /tmp/test_encapsia_backup

test "Restore from the backup"
encapsia database restore --yes /tmp/test_encapsia_backup
sleep 5
# Cleanup
rm /tmp/test_encapsia_backup