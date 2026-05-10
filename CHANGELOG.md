# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-10

### Added
- Regex support with `r:pattern` tag (case-insensitive).
- Multi-column extraction support (e.g., `col:1,3` or `col:1-4`).
- Custom delimiter support with `sep:X` (e.g., `sep:,`).
- New `--filter` (`-f`) output mode to return filtered results instead of the command recipe.
- In-TUI help hint for discovered tags in the header.
- New `--version` flag.
- Fish shell widget documentation in README.
- Performance caching in `filter_lines` for smoother UI on large datasets.

### Fixed
- Fatal `NameError: os is not defined` bug on startup.
- Misleading examples in README now correctly use `--filter`.
- Infinite redraw loop in ultra-small terminals.
- Improved Zsh widget to stage commands instead of immediate execution.
- Added validation for `col:0` to prevent unintended `awk $0` output.
- Strengthened `test_broken_pipe_handling` with a real integration test.

### Changed
- Moved `test_usecases.py` to `tests/` and converted it to a standard unit test.
- Added integration and shell injection security tests.

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
