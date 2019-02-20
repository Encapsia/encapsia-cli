# About

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

# TODO

* Add an encapsia-launch-httpie command which sets the environment appropriately (replaces old ice-api command)
* Fix: it is not possible to get the help of a sub-command without having ENCAPSIA_HOST set or give --host option
* Add some tests which exercise the command line, and illustrate it's use, with a real server.
* Sync with https://bitbucket.org/cmedtechnology/icetools/src/6f7008db6133?at=refactor_tools
* Check out https://bitbucket.org/cmedtechnology/iceapi/src/6a1093e0ae91/iceapi/?at=add_api
* ice-copy-entities
* ice-trialconfig