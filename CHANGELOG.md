# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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