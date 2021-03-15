# About

[![Known Vulnerabilities](https://snyk.io/test/github/tcorbettclark/encapsia-cli/badge.svg?targetFile=requirements.txt)](https://snyk.io/test/github/tcorbettclark/encapsia-cli?targetFile=requirements.txt)

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

## Autocomplete

Setup autocomplete using the instructions found on <https://github.com/click-contrib/click-completion>

## Tests

See the `walkthrough_tests` directory for bash scripts which exercise the CLI.

Run them e.g. with:

    bash walkthrough_tests/all.sh

or test specific subcommands with:

    bash walkthrough_tests/token.sh

Note that these tests are *not* self-verifying; they just provide helpful coverage, assurance, and working documentation.

## Release checklist

* Run: `black .`
* Run: `isort .`
* Run: `flake8 .`
* Run: `mypy .`
* Ensure "tests" run ok (see above).
* Capture test output and commit with: `bash walkthrough_tests/all.sh 2>&1 | ansi2html -f 80% >WALKTHROUGH.html`
* Create `requirements.txt` for Snyk scanning with: `poetry export -f requirements.txt >requirements.txt`
* Ensure git tag, package version, and `enacpsia_cli.__version__` are all equal.