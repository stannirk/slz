# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-05-09

### Changed
- Project renamed from "sluice" to "slz" for punchy 3-letter CLI convention.
- Updated documentation and tests to reflect the new identity.

## [0.1.1] - 2026-05-09

## [0.1.0] - 2026-05-09

### Added
- Initial release of SLZ.
- Interactive TUI for filtering piped input.
- `col:N` tag for smart column extraction with `awk`.
- Asynchronous streaming input for responsiveness.
- Virtual scrolling (Arrow keys, Page Up/Down) for large datasets.
- Modern Python packaging with `hatchling` and `pyproject.toml`.
- Comprehensive unit test suite including chaos and stress tests.
- GitHub Actions CI for automated testing across Python 3.8-3.12.
- Type hints for better developer experience.
- Graceful handling of small terminal sizes.
