#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

start_tests

test "Set a config value to a string"
encapsia config set test_string \"a_string\"
encapsia config get test_string

test "Set a config value to a number"
encapsia config set test_number 123
encapsia config get test_number

test "Set a config value to a list"
encapsia config set test_list '["a", 1]'
encapsia config get test_list

test "Delete config values"
encapsia config delete test_string
encapsia config delete test_number
encapsia config delete test_list

test "Save config to a file and load it again"
encapsia config save /tmp/test_encapsia_config.json
cat /tmp/test_encapsia_config.json

# Remove the root_token because it is hidden and we cannot set it again.
cat /tmp/test_encapsia_config.json | python -c "import json, sys; c=json.load(sys.stdin); del c['root_token']; print(json.dumps(c))" > /tmp/test_encapsia_config2.json
encapsia config load /tmp/test_encapsia_config2.json

# Cleanup.
rm /tmp/test_encapsia_config*.json

test "Show the entire config"
encapsia config show