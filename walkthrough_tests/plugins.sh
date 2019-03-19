#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1
[ -z "$EXAMPLE_PLUGIN_SRC" ] && echo "Please provide example plugin src directory --example-plugin-src argument" && exit 1

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

start_tests

test "Build the example plugin from src"
encapsia plugins --force build-from-src $EXAMPLE_PLUGIN_SRC

test "Requst a build again, but this time it should be skipped over because it already exists in the cache"
encapsia plugins build-from-src $EXAMPLE_PLUGIN_SRC

test "Move the example plugin out of the cache and then add it back in directly"
mv ~/.encapsia/plugins-cache/plugin-example-0.0.1.tar.gz /tmp/
encapsia plugins fetch-from-url file:///tmp/plugin-example-0.0.1.tar.gz

test "Build the launch plugin from legacy S3 (after first removing from the cache)"
rm -f ~/.encapsia/plugins-cache/plugin-launch-*.tar.gz
encapsia plugins build-from-legacy-s3 --versions=s3_plugins.toml --email=test_user@encapsia.com

test "Second time should be skipped over because it is already in the cache"
encapsia plugins build-from-legacy-s3 --versions=s3_plugins.toml --email=test_user@encapsia.com

test "Install the example plugin from the cache, then uninstall it"
encapsia plugins install --versions=example.toml
encapsia plugins --force uninstall example

test "Dev update the example plugin from scratch"
encapsia plugins --force dev-update $EXAMPLE_PLUGIN_SRC

test "Second time round there is nothing to do because nothing has changed"
encapsia plugins dev-update $EXAMPLE_PLUGIN_SRC

test "Modify the example plugin and update again. This time only the tasks should be updated"
touch $EXAMPLE_PLUGIN_SRC/tasks/test_new_module.py
encapsia plugins dev-update $EXAMPLE_PLUGIN_SRC
rm $EXAMPLE_PLUGIN_SRC/tasks/test_new_module.py

test "Uninstall the example plugin"
encapsia plugins --force uninstall example

test "Create and destroy new namespace"
encapsia plugins dev-create-namespace testing123
encapsia plugins dev-destroy-namespace testing123

test "Get info on all plugins"
encapsia plugins info