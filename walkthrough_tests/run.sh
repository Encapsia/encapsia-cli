#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1
[ -z "$EXAMPLE_PLUGIN_SRC" ] && echo "Please provide example plugin src directory --example-plugin-src argument" && exit 1

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

start_tests

test "(Setup) Install the example plugin from src"
encapsia plugins dev-update --reset $EXAMPLE_PLUGIN_SRC

test "Run basic test function"
encapsia run task example test_module.test_function name=tim

test "Run basic test function and save result to file"
encapsia run task example test_module.test_function --save-as /tmp/encapsia_test_save_from_task.txt name=tim
echo $(cat /tmp/encapsia_test_save_from_task.txt)
rm /tmp/encapsia_test_save_from_task.txt

test "Run basic test function with blank argument"
encapsia run task example test_module.test_function name=

test "Run test function written with fixed arguments"
encapsia run task example test_module.test_function_with_fixed_args name=tim

test "Run test function accepting any arguments"
encapsia run task example test_module.test_function_with_any_args a=1 b=2 c=3

test "Run test function which only takes meta as a fixed argument"
encapsia run task example test_module.test_function_with_meta_as_fixed_arg

test "Run function expecting uploaded data."
encapsia run task example test_module.test_function_for_posted_data --upload=example_data.txt

# The following should fail, so have an " || true" at the end to keep these tests running.

test "Run function which takes no arguments. This *should* fail!!!"
encapsia run task example test_module.test_function_with_no_args || true

test "Run function with fixed arg and no meta. This *should* fail!!!"
encapsia run task example test_module.test_function_with_single_arg_and_no_meta name=tim || true

test "Run function with arg and no meta. This *should* fail!!!"
encapsia run task example test_module.test_function_with_single_kwarg name=tim || true

test "Run function expecting uploaded data but without any data. This *should* fail!!!"
encapsia run task example test_module.test_function_for_posted_data || true