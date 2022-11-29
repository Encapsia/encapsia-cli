# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [next]

### Fixed

- Fixed installing plugin using file path. #76.
- `plugins add` will now abort if it cannot find some of the requested specs in S3
- Clocked several dependencies patching vulnerabilities and other issues.
- Replaced implementation using `tarfile.extractall` of `encapsia plugins ls`, that is
  vulnerable to a path traversal attack. See
  https://github.com/python/cpython/issues/73974 and
  https://www.trellix.com/en-us/about/newsroom/stories/research/tarfile-exploiting-the-world.html

### Added

- Support for adding to local_store groups of plugins with one command. #87.
- Support for installing groups of plugins with one command. #87.
- A new `token transfer` subcommand, allowing to obtain a token for a different user (current user's credentials permitting) and printing it out as plain text or shell command setting encapsia environment variables.
- A new `token env` subcommand that just prints out shell commands to set environment variables `ENCAPSIA_URL` and `ENCAPSIA_TOKEN`.

### Changed

- Display a message when a config get key is missing, instead of a traceback. #62.
- Replaced request to deprecated pluginsmanager API. #79.
- The `token extend` subcommand gained ability to display extended token (both as plain text or as shell commands setting environment), instead of storing in credentials file.
- The `token extend` now allows you to set capabilities (as a subset of existing capabilities).

## [0.5.1] - 2021-10-19

### Changed

- Remove local implementation for resilient calls, use implementation from encapsia-api>=0.3.1

## [0.5.0] - 2021-06-08

### Added

- Support for plugin variants (#70).
- Added a few unit tests.

### Changed

- Refactored module plugins extracting parts into pluginsinfo and s3 modules.
- Changed display for plugins subcommands `ls`, `upstream` and `status`.

### Fixed

- Retry after connection errors and timeouts (in selected cases).
- Fixed `encapsia plugins add --latest-existing`
- Make CLI return an exit code indicating error when plugin installation fails. Fixes #42.

## [0.4.1] - 2021-03-15

### Fixed

- Fix Bug #50 whereby `ENCAPSIA_URL` and `ENCAPSIA_TOKEN` were never being discovered and used.

## [0.4.0] - 2020-12-07

### Added

- Support for searching S3 buckets for plugins below specified paths.

## [0.3.3] - 2020-10-27

### Fixed

- Fixed bug which created a `cwd/plugins-local-dir/` folder e.g. when running `encapsia plugins --force dev-update .`

## [0.3.2] - 2020-10-26

### Fixed

- Fixed bug which prevented pre-release semver compatible version numbers for plugins. #46.

## [0.3.1] - 2020-10-15

### Fixed

- Fixed bug which prevented local store from being updated from a versions TOML file.

## [0.3.0] - 2020-09-15

### Changed

- Moved the `--host` option to the top level. So e.g. `encapsia users --host foo` is now `encapsia --host foo users`.
- Changed all `--yes` options to `--force` for consistency.
- Changed `encapsia httpie shell` to `encapsia httpie` because it can only launch interactive httpie.

### Added

- Added support for providing options in a `~/.encapsia/config.toml` file.
- Added uniform support for providing options as env vars following click conventions. E.g.
  `ENCAPSIA_HOST` and `ENCAPSIA_PLUGINS_LOCAL_DIR`.
- Added support for upstream sources of plugins from multiple S3 buckets.

### Fixed

- Don't use `datetime.datetime.fromisoformat` because it is not present in Python 3.6.

## [0.2.3] - 2020-09-08

### Added

- A changelog!

### Fixed

- Removed traceback from users without roles (by upgrading to latest encapsia-api)
