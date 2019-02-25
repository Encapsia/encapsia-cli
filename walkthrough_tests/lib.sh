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
        EXAMPLE_PLUGIN_SRC=$(realpath "$2")
        shift # past argument
        shift # past value
        ;;
        *)
        shift # past unknown
        ;;
    esac
done


# Pretty print the test descriptions.
function test() {
    echo -e "\n\e[93m\e[1m=== $1 ===\e[0m"
}


function start_tests() {
    # Always fail on error.
    set -e

    # Log commands except for echo because they are used to explain what is being done.
    trap '[[ $BASH_COMMAND != test* ]] && echo -e ">${BASH_COMMAND}"' DEBUG
}