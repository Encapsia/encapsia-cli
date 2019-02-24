# About

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

# Autocomplete

Setup autocomplete using the instructions found on https://github.com/click-contrib/click-completion.

# Release checklist

* Ensure git tag, package version, and enacpsia_cli.__version__ are all equal.

# TODO

* Remove dbctl subcommand (after checking we don't need the non-backup and non-fixture subcommands)

* Add some tests which exercise the command line, and illustrate it's use, with a real server.
* Sync with https://bitbucket.org/cmedtechnology/icetools/src/6f7008db6133?at=refactor_tools
* Check out https://bitbucket.org/cmedtechnology/iceapi/src/6a1093e0ae91/iceapi/?at=add_api
* ice-copy-entities
* ice-trialconfig