# About

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

# Autocomplete

Setup autocomplete using the instructions found on https://github.com/click-contrib/click-completion.

# Tests

See the `walkthrough_tests` directory for bash scripts which exercise the CLI.

Run them e.g. with:

    bash walkthrough_tests/all.sh --host <host> --example-plugin-src ../inf-ice-example-plugin/

Note that these tests are *not* self-verifying; they just provide helpful coverage, assurance, and working documentation.

# Release checklist

* Ensure "tests" run ok (see above). Also capture output and commit with:
    `bash walkthrough_tests/all.sh --host tcc24 --example-plugin-src ../inf-ice-example-plugin/ 2>&1 | ansi2html -f 80% >WALKTHROUGH.html`
* Run: `black .`
* Run: `isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width=88 -y`
* Run: `flake8 --ignore=E501 .`
* Ensure git tag, package version, and `enacpsia_cli.__version__` are all equal.

# TODO

* Find a better way to force color mode e.g. for walkthrough.html than fiddling `encapsia.py`
* Add sending files to views (once PR accepted)
* Use click-web to create an encapsia webserve command?? Put in a plugin?
* Validate input to plugins uninstall
* Add an "encapsia plugins dev-server" command to forward calls to localhost to remote, thus allowing easier dev without installing anything except the SQL.

* Sync with https://bitbucket.org/cmedtechnology/icetools/src/6f7008db6133?at=refactor_tools
* Check out https://bitbucket.org/cmedtechnology/iceapi/src/6a1093e0ae91/iceapi/?at=add_api
* ice-copy-entities
* ice-trialconfig