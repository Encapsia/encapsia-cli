#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

start_tests

test "Build the walkthrough_test plugin from src"
encapsia plugins --force dev-build test_plugin

test "Request a build again, but this time it should be skipped over because it already exists in the local store"
encapsia plugins dev-build test_plugin

test "Move the walkthrough_test plugin out of the local store and then add it back in directly"
mv ~/.encapsia/plugins/plugin-walkthrough_test-0.0.1.tar.gz /tmp/
encapsia plugins add file:///tmp/plugin-walkthrough_test-0.0.1.tar.gz

test "Install the walkthrough_test plugin from the local store, then uninstall it"
encapsia plugins --force install --versions=example.toml --show-logs
encapsia plugins --force uninstall walkthrough_test --show-logs

test "Dev update the walkthrough_test plugin from scratch"
encapsia plugins --force dev-update test_plugin

test "Second time round there is nothing to do because nothing has changed"
encapsia plugins dev-update test_plugin

test "Modify the walkthrough_test plugin and update again. This time only the tasks should be updated"
touch test_plugin/tasks/test_new_module.py
encapsia plugins dev-update test_plugin
rm test_plugin/tasks/test_new_module.py

test "Install the non-dev version of the walkthrough_test plugin so we can uninstall it (to be tidy)."
encapsia plugins --force install --versions=example.toml
encapsia plugins --force uninstall walkthrough_test

test "Create and destroy new namespace"
encapsia plugins dev-create testing123
encapsia plugins dev-destroy testing123

test "Fetch a few specific plugins from S3, install launch, and show the logs"
encapsia plugins add --versions example_plugins.toml
encapsia plugins --force install launch
encapsia plugins logs launch

test "Fetch latest plugins from S3, install launch, and show the logs"
encapsia plugins add --latest-existing
encapsia plugins --force install launch
encapsia plugins logs launch

test "Uninstall launch and show the logs"
encapsia plugins --force uninstall launch
encapsia plugins logs launch

test "Get status on all installed plugins"
encapsia plugins status

test "Get info on latest plugins in the local store"
encapsia plugins ls
encapsia plugins ls -l

test "Get info on upstream plugins"
encapsia plugins upstream
encapsia plugins upstream conduct-1.6 --all-versions
