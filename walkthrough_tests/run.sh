#/usr/bin/env bash

# Load "library" code
source $(dirname "$0")/lib.sh

# Validate input arguments.
[ -z "$ENCAPSIA_HOST" ] && echo "Please provide host using --host argument" && exit 1
[ -z "$EXAMPLE_PLUGIN_SRC" ] && echo "Please provide example plugin src directory --example-plugin-src argument" && exit 1

# Change directory to this test directory for relative paths.
cd $(dirname "$0")

start_tests

test "(Setup for running views or tasks etc) Install the example plugin from src"
encapsia plugins --force dev-update $EXAMPLE_PLUGIN_SRC

# The views

test "Run view with no arguments"
encapsia run view example test_no_args

test "Run view and save result to file"
encapsia run view example test_no_args --save-as /tmp/encapsia_test_save_from_view.txt
echo $(cat /tmp/encapsia_test_save_from_view.txt)
rm /tmp/encapsia_test_save_from_view.txt

test "Run view with one argument"
encapsia run view example test_one_arg hello

test "Run view with two arguments"
encapsia run view example test_two_args "hello" " world"

test "Run view with no arguments to return meta"
encapsia run view example test_only_meta

test "Run view with one optional argument"
encapsia run view example test_one_optional_arg
encapsia run view example test_one_optional_arg limit=999

test "Run view with mixture of argument types"
encapsia run view example test_mixture hello limit=123

test "Run view which returns CSV directly"
encapsia run view example example_view_function_as_csv_file

test "Run view which returns JSON directly"
encapsia run view example example_view_function_as_json_file

# The tasks

test "Run basic test task function"
encapsia run task example test_module.test_function name=tim

test "Run basic test task function and save result to file"
encapsia run task example test_module.test_function --save-as /tmp/encapsia_test_save_from_task.txt name=tim
echo $(cat /tmp/encapsia_test_save_from_task.txt)
rm /tmp/encapsia_test_save_from_task.txt

test "Run basic test task function with blank argument"
encapsia run task example test_module.test_function name=

test "Run test task function written with fixed arguments"
encapsia run task example test_module.test_function_with_fixed_args name=tim

test "Run test task function accepting any arguments"
encapsia run task example test_module.test_function_with_any_args a=1 b=2 c=3

test "Run test task function which only takes meta as a fixed argument"
encapsia run task example test_module.test_function_with_meta_as_fixed_arg

test "Run task function expecting uploaded data."
encapsia run task example test_module.test_function_for_posted_data --upload=example_data.txt

# The failing tasks. These should fail so have an " || true" at the end to keep these tests running.

test "Run task function which takes no arguments. This *should* fail!!!"
encapsia run task example test_module.test_function_with_no_args || true

test "Run task function with fixed arg and no meta. This *should* fail!!!"
encapsia run task example test_module.test_function_with_single_arg_and_no_meta name=tim || true

test "Run task function with arg and no meta. This *should* fail!!!"
encapsia run task example test_module.test_function_with_single_kwarg name=tim || true

test "Run task function expecting uploaded data but without any data. This *should* fail!!!"
encapsia run task example test_module.test_function_for_posted_data || true

# The jobs

test "Run job function, showing 2 joblog entries with status queued and success"""
encapsia run job example test_module.test_function_for_a_job name=tim