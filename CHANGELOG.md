# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Don't use datetime.datetime.fromisoformat because it is not present in 3.6.

## [0.2.3] - 2020-09-08

### Added

- A changelog!

### Fixed

- Removed traceback from users without roles (by upgrading to latest encapsia-api)