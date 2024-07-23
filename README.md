# About

![Workflows](https://github.com/encapsia/encapsia-cli/actions/workflows/main.yml/badge.svg)
![PyPI](https://img.shields.io/pypi/v/encapsia-cli?style=flat)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/encapsia-cli)

[![Known Vulnerabilities](https://snyk.io/test/github/encapsia/encapsia-cli/badge.svg?targetFile=pyproject.toml)](https://snyk.io/test/github/encapsia/encapsia-cli?targetFile=requirements.txt)

This package provides command line access to Encapsia over the REST API.

All of these are designed to work with server 1.5 and beyond.

## Autocomplete

Setup autocomplete using the instructions found on <https://github.com/click-contrib/click-completion>

## Tests

### Unit tests

Run:

    poetry run pytest

### Walkthrough Tests

Prerequisite: an instance of ice must be running on your localhost, and valid token for
it must be present in your key store.

See the `walkthrough_tests` directory for bash scripts which exercise the CLI.

Run them e.g. with:

    poetry run bash walkthrough_tests/all.sh

or test specific subcommands with:

    poetry run bash walkthrough_tests/token.sh

Note that these tests are *not* self-verifying; they just provide helpful coverage,
assurance, and working documentation.

## Release checklist

* Run: `poetry run black .`
* Run: `poetry run isort .`
* Run: `poetry run flake8 .`
* Run: `poetry run mypy .`
* Ensure "tests" run ok (see above).
* Capture test output and commit with: `poetry run bash walkthrough_tests/all.sh 2>&1 | poetry run ansi2html -f 80% >WALKTHROUGH.html`
* Create `requirements.txt` for Snyk scanning with: `poetry export -f requirements.txt >requirements.txt`
* Ensure git tag, package version, and `encapsia_cli.__version__` are all equal.
