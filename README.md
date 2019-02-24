# About

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

# Autocomplete

Setup autocomplete using the instructions found on https://github.com/click-contrib/click-completion.

# Release checklist

* Ensure git tag, package version, and enacpsia_cli.__version__ are all equal.

# TODO

* Test run view and run task once updated plugins.
* Add sending files to views and tasks.
* Add saving output from views and tasks to a file.

* Review what is being used in lib. log vs click.echo. See log_error?
* Update the "tests"
* Validate input to plugins uninstall

* Sync with https://bitbucket.org/cmedtechnology/icetools/src/6f7008db6133?at=refactor_tools
* Check out https://bitbucket.org/cmedtechnology/iceapi/src/6a1093e0ae91/iceapi/?at=add_api
* ice-copy-entities
* ice-trialconfig