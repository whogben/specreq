"""Tests for Req validation, trees, serialization, and spec loading."""

import json
from pathlib import Path
from typing import Literal

import pytest

from specreq import Req, load_spec, _REQ_REGISTRY


# --- Test req definitions ---

_order: list[str] = []


class TrackReq(Req):
    """Records tag in _order when validate runs."""
    kind: Literal["_test_track"] = "_test_track"
    tag: str = ""

    def validate(self, product: Path) -> list[str]:
        _order.append(self.tag)
        return []


class BadReq(Req):
    """Returns an issue."""
    kind: Literal["_test_bad"] = "_test_bad"

    def validate(self, product: Path) -> list[str]:
        return ["issue"]


class BoomReq(Req):
    """Raises during validate."""
    kind: Literal["_test_boom"] = "_test_boom"

    def validate(self, product: Path) -> list[str]:
        raise ValueError("boom")


class SkipReq(Req):
    """Overrides _validate to skip child walk."""
    kind: Literal["_test_skip"] = "_test_skip"

    def _validate(self, product: Path, *, survive_exceptions: bool = True) -> list[str]:
        return ["custom"]


class ConfiguredReq(Req):
    """Req with typed fields."""
    kind: Literal["_test_cfg"] = "_test_cfg"
    name: str
    port: int = 8080


class PassReq(Req):
    """Always passes validation."""
    kind: Literal["_test_pass"] = "_test_pass"


# --- Fixtures ---

@pytest.fixture(autouse=True)
def _clear_order():
    _order.clear()
    yield


# --- Validate order ---

def test_validate_runs_children_before_parent():
    p = TrackReq(tag="parent", children=[TrackReq(tag="child")])
    p._validate(Path("/tmp"))
    assert _order == ["child", "parent"]


def test_three_level_validate_order():
    root = TrackReq(tag="l1", children=[
        TrackReq(tag="l2", children=[TrackReq(tag="l3")])
    ])
    root._validate(Path("/tmp"))
    assert _order == ["l3", "l2", "l1"]


# --- Issues and errors ---

def test_custom_validate_issues():
    assert BadReq()._validate(Path("/tmp")) == ["issue"]


def test_override_validate_skips_default_child_walk():
    parent = SkipReq(children=[BadReq()])
    assert parent._validate(Path("/tmp"), survive_exceptions=True) == ["custom"]


def test_survive_exceptions_records_traceback():
    issues = BoomReq()._validate(Path("/tmp"), survive_exceptions=True)
    assert len(issues) == 1
    assert "exception at" in issues[0]
    assert "ValueError: boom" in issues[0]
    assert "Traceback (most recent call last)" in issues[0]


def test_survive_exceptions_false_propagates():
    with pytest.raises(ValueError, match="boom"):
        BoomReq()._validate(Path("/tmp"), survive_exceptions=False)


def test_mixed_child_issues_parent_still_runs():
    p = TrackReq(tag="parent", children=[BadReq(), TrackReq(tag="ok")])
    issues = p._validate(Path("/tmp"))
    assert _order == ["ok", "parent"]
    assert "issue" in issues


def test_mixed_child_raise_sibling_and_parent_still_run():
    p = TrackReq(tag="parent", children=[BoomReq(), TrackReq(tag="ok")])
    issues = p._validate(Path("/tmp"))
    assert _order == ["ok", "parent"]
    assert len(issues) == 1
    assert "ValueError: boom" in issues[0]


# --- Serialization round-trip ---

def test_serialization_roundtrip():
    original = ConfiguredReq(name="svc", port=9000, children=[
        PassReq(),
        TrackReq(tag="inner"),
    ])
    data = original.model_dump()
    loaded = load_spec(data)

    assert len(loaded) == 1
    root = loaded[0]
    assert isinstance(root, ConfiguredReq)
    assert root.name == "svc"
    assert root.port == 9000
    assert len(root.children) == 2
    assert isinstance(root.children[0], PassReq)
    assert isinstance(root.children[1], TrackReq)
    assert root.children[1].tag == "inner"

    # Dict round-trip (the supported path)
    loaded2 = load_spec(data)
    assert isinstance(loaded2, list)
    assert loaded2[0].model_dump() == data


# --- load_spec ---

def test_load_spec_single_root_from_dict():
    roots = load_spec({"kind": "_test_cfg", "name": "x"})
    assert len(roots) == 1
    assert isinstance(roots[0], ConfiguredReq)
    assert roots[0].name == "x"


def test_load_spec_multiple_roots():
    roots = load_spec([
        {"kind": "_test_pass"},
        {"kind": "_test_cfg", "name": "y", "port": 3000},
    ])
    assert len(roots) == 2
    assert isinstance(roots[0], PassReq)
    assert isinstance(roots[1], ConfiguredReq)
    assert roots[1].port == 3000


def test_load_spec_from_file(tmp_path):
    f = tmp_path / "test.spec.json"
    f.write_text(json.dumps({"kind": "_test_pass"}))
    roots = load_spec(f)
    assert len(roots) == 1
    assert isinstance(roots[0], PassReq)


def test_load_spec_unknown_kind():
    with pytest.raises(ValueError, match="Unknown req kind"):
        load_spec({"kind": "nonexistent"})


# --- Registry ---

def test_auto_registration():
    assert _REQ_REGISTRY["_test_pass"] is PassReq
    assert _REQ_REGISTRY["_test_cfg"] is ConfiguredReq
    assert _REQ_REGISTRY["_test_track"] is TrackReq
