"""Tests for the publish script and project consistency checks."""

import re
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"


def test_changelog_latest_version_matches_pyproject():
    """The most recent version header in CHANGELOG.md must match pyproject.toml."""
    with open(PYPROJECT, "rb") as f:
        pyproject_version = tomllib.load(f)["project"]["version"]

    text = CHANGELOG.read_text()
    versions = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)
    assert versions, "No version headers found in CHANGELOG.md"
    latest = versions[0]
    assert latest == pyproject_version, (
        f"Changelog latest is [{latest}] but pyproject.toml is [{pyproject_version}]"
    )
