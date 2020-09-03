#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1
[ -z "$EXAMPLE_PLUGIN_SRC" ] && echo "Please provide example plugin src directory using --example-plugin-src argument" && exit 1

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

start_tests

test "Build the example plugin from src"
encapsia plugins --force dev-build $EXAMPLE_PLUGIN_SRC

test "Request a build again, but this time it should be skipped over because it already exists in the local store"
encapsia plugins dev-build $EXAMPLE_PLUGIN_SRC

test "Move the example plugin out of the local store and then add it back in directly"
mv ~/.encapsia/plugins/plugin-example-0.0.1.tar.gz /tmp/
encapsia plugins add file:///tmp/plugin-example-0.0.1.tar.gz

test "Install the example plugin from the local store, then uninstall it"
encapsia plugins --force install --versions=example.toml --show-logs
encapsia plugins --force uninstall example --show-logs

test "Dev update the example plugin from scratch"
encapsia plugins --force dev-update $EXAMPLE_PLUGIN_SRC

test "Second time round there is nothing to do because nothing has changed"
encapsia plugins dev-update $EXAMPLE_PLUGIN_SRC

test "Modify the example plugin and update again. This time only the tasks should be updated"
touch $EXAMPLE_PLUGIN_SRC/tasks/test_new_module.py
encapsia plugins dev-update $EXAMPLE_PLUGIN_SRC
rm $EXAMPLE_PLUGIN_SRC/tasks/test_new_module.py

test "Install the non-dev version of the example plugin so we can uninstall it (to be tidy)."
encapsia plugins --force install --versions=example.toml
encapsia plugins --force uninstall example

test "Create and destroy new namespace"
encapsia plugins dev-create testing123
encapsia plugins dev-destroy testing123

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
