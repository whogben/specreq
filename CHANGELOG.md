# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
before v1.0.0, breaking changes bump minor version and additive changes bump patch version, after v1.0.0 this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-19

### Changed

- **Breaking:** `Requirement` replaced by `Req` (Pydantic BaseModel subclass) with a `kind` discriminator field for JSON-driven deserialization.
- **Breaking:** Specs are now JSON files (not Python modules). CLI auto-discovers from `specs/` and `products/` directories.
- **Breaking:** `--save` flag removed — specs are authored as JSON directly.
- `load_spec()` deserializes JSON (file path, dict, or list) into typed `Req` trees using a `kind`-based registry.
- `Req.model_dump()` serializes preserving actual subclass fields and children.
- CLI imports `reqs/` directory for `Req` subclass auto-registration.
- Validation behavior (children-before-parent, survive_exceptions, --strict) unchanged.

### Removed

- `Requirement` class, `to_dict()`, `export_roots()`, `reset()`, instance registry.
- `--save` CLI flag.
- `plans/specreq-next-steps.md`.

## [0.1.2] - 2026-05-18

### Added

- `Changelog` project URL in `pyproject.toml` (shows in PyPI sidebar).
- Changelog link in README.md.

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
