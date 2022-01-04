#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Get whoami info about current token"
encapsia token whoami

test "Display shell commands to set ENCAPSIA_URL and ENCAPSIA_TOKEN environment variables for host"
encapsia token env

test "Extend lifespan of token (changes the encapsia credentials)"
encapsia token extend
encapsia token whoami

test "Transfer (get new token) to specified user. Stored token *should not* change!"
encapsia users add-superuser user1@cmedtechnology.com User One
encapsia token transfer user1@cmedtechnology.com
encapsia token whoami

# Don't normally run the following because it is too distructive!
# test "Expire current token"
# encapsia token expire
