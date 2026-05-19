"""Tests for the specreq CLI."""

import json
from pathlib import Path
from typing import Literal

from typer.testing import CliRunner

from specreq import Req
from specreq.cli import app

runner = CliRunner()


# --- CLI test reqs ---

class _PassReq(Req):
    kind: Literal["_cli_pass"] = "_cli_pass"


class _BadReq(Req):
    kind: Literal["_cli_bad"] = "_cli_bad"

    def validate(self, product: Path) -> list[str]:
        return ["issue"]


class _BoomReq(Req):
    kind: Literal["_cli_boom"] = "_cli_boom"

    def validate(self, product: Path) -> list[str]:
        raise ValueError("boom")


# --- Helpers ---

def _make_project(tmp: Path, spec_json: str, product_name: str = "my_product") -> Path:
    """Create a minimal project layout in tmp and return it."""
    (tmp / "reqs").mkdir()
    (tmp / "specs").mkdir()
    (tmp / "products" / product_name).mkdir(parents=True)
    (tmp / "specs" / "test.spec.json").write_text(spec_json)
    return tmp


SINGLE = json.dumps({"kind": "_cli_pass"})
TWO_ROOTS = json.dumps([{"kind": "_cli_pass"}, {"kind": "_cli_pass"}])
WITH_ISSUE = json.dumps({"kind": "_cli_bad"})
WITH_ERROR = json.dumps({"kind": "_cli_boom"})
UNKNOWN = json.dumps({"kind": "nonexistent"})


# --- Auto-discovery tests ---

def test_auto_discover_single_spec_single_product(tmp_path, monkeypatch):
    project = _make_project(tmp_path, SINGLE)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Valid." in result.stdout
    assert "1 root(s) passed" in result.stdout


def test_auto_discover_requires_project_layout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No specs/" in result.stdout


def test_auto_discover_ambiguous_specs(tmp_path, monkeypatch):
    project = _make_project(tmp_path, SINGLE)
    (project / "specs" / "other.spec.json").write_text(SINGLE)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Multiple specs" in result.stdout


def test_auto_discover_ambiguous_products(tmp_path, monkeypatch):
    project = _make_project(tmp_path, SINGLE)
    (project / "products" / "other_product").mkdir()
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Multiple products" in result.stdout


# --- Explicit paths (override auto-discovery) ---

def test_explicit_spec_and_product(tmp_path, monkeypatch):
    project = _make_project(tmp_path, SINGLE)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["specs/test.spec.json", f"products/my_product"])
    assert result.exit_code == 0


def test_explicit_spec_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["nope.json", str(tmp_path)])
    assert result.exit_code == 1
    assert "Spec file not found" in result.stdout


def test_explicit_product_missing(tmp_path, monkeypatch):
    project = _make_project(tmp_path, SINGLE)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["specs/test.spec.json", "products/nope"])
    assert result.exit_code == 1
    assert "Product path does not exist" in result.stdout


# --- Validation behavior ---

def test_two_roots(tmp_path, monkeypatch):
    project = _make_project(tmp_path, TWO_ROOTS)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "2 root(s) passed" in result.stdout


def test_with_issues(tmp_path, monkeypatch):
    project = _make_project(tmp_path, WITH_ISSUE)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "issue" in result.stdout


def test_survive_includes_traceback(tmp_path, monkeypatch):
    project = _make_project(tmp_path, WITH_ERROR)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Traceback" in result.stdout
    assert "exception at" in result.stdout


def test_strict_propagates(tmp_path, monkeypatch):
    project = _make_project(tmp_path, WITH_ERROR)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--strict"])
    assert result.exit_code == 1
    assert result.exception is not None


def test_unknown_kind(tmp_path, monkeypatch):
    project = _make_project(tmp_path, UNKNOWN)
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Unknown req kind" in result.stdout


def test_invalid_json(tmp_path, monkeypatch):
    project = _make_project(tmp_path, "not json")
    monkeypatch.chdir(project)
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Failed to load spec" in result.stdout
