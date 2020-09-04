# Pretty print a banner separator.
function banner() {
    echo -e "\n$(tput setaf 6)<<< $1 >>>$(tput sgr0)"
}

# Pretty print the test descriptions.
function test() {
    echo -e "\n$(tput setaf 4)=== $1 ===$(tput sgr0)"
}


function start_tests() {
    # Always fail on error.
    set -e

    # Log commands except for echo because they are used to explain what is being done.
    trap '[[ $BASH_COMMAND != test* ]] && echo -e ">${BASH_COMMAND}"' DEBUG
}

# Assume that we are using the localhost server instance.
export ENCAPSIA_HOST=localhost