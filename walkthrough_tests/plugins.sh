#/usr/bin/env bash

# Quick-and-dirty parse arguments.
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        --host)
        export ENCAPSIA_HOST="$2"
        shift # past argument
        shift # past value
        ;;
        --example-plugin-src)
        EXAMPLE_PLUGIN_SRC="$2"
        shift # past argument
        shift # past value
        ;;
        *)
        echo "Please provide --host and --example-plugin-src arguments."
        exit 1
        ;;
    esac
done

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1
[ -z "$EXAMPLE_PLUGIN_SRC" ] && echo "Please provide example plugin src directory --example-plugin-src argument" && exit 1

# Make plugin path absolute because we will change directory later.
EXAMPLE_PLUGIN_SRC=$(realpath $EXAMPLE_PLUGIN_SRC)

# Tell the user what variables are being used.
echo "Exercise encapsia plugins command."
echo "These are *not* self-verifying tests, so check the output for reasonableness!"
echo
echo "Using host: $ENCAPSIA_HOST"
echo "Using example src plugin code: $EXAMPLE_PLUGIN_SRC"

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

# Pretty print the test descriptions.
function test() {
    echo -e "\n\e[92m\e[1m=== $1 ===\e[0m"
}

# Always fail on error.
set -e

# Log commands except for echo because they are used to explain what is being done.
trap '[[ $BASH_COMMAND != test* ]] && echo -e ">${BASH_COMMAND}"' DEBUG


# WALKTHROUGH STARTS HERE...

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

test "Install the example plugin form the cache, then uninstall it"
encapsia plugins install --versions=example.toml
encapsia plugins --force uninstall example

test "Dev update the example plugin from scratch"
encapsia plugins dev-update $EXAMPLE_PLUGIN_SRC --reset

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