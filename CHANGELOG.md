# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
before v1.0.0, breaking changes bump minor version and additive changes bump patch version, after v1.0.0 this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-05-18

### Added

- `readme = "README.md"` in `pyproject.toml` so README content appears on PyPI.
- Publish script now checks that `pyproject.toml` declares a readme field.
- Publish script now verifies the local version is newer than what's on PyPI.
- Test that all README.md links are absolute URLs (work on PyPI, not just GitHub).

## [0.1.0] - 2026-05-18

### Added

- `Requirement` tree type: optional Pydantic config, parent/children, `validate` / `_validate` over `Path`, `survive_exceptions` on `_validate`, instance registry and `reset()`.
- Serialization: `to_dict()` and `export_roots()` for spec trees (JSON-friendly).
- `specreq` CLI: `validate` with positional spec (file path or dotted module) and product directory; `--save` writes exported roots as JSON; `--strict` disables per-node exception catching in `_validate`.
- Development extras (`[dev]`) with pytest.
