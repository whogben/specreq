"""Unit tests for Requirement validation order, trees, and serialization."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from specreq import Requirement


def test_validate_runs_children_before_parent():
    Requirement.reset()
    order: list[str] = []

    class Child(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("child")
            return []

    class Parent(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("parent")
            return []

    p = Parent()
    Child(parent=p)

    product = Path("/tmp")
    p._validate(product)
    assert order == ["child", "parent"]


def test_custom_validate_issues():
    Requirement.reset()

    class R(Requirement):
        def validate(self, product: Path) -> list[str]:
            return ["bad"]

    r = R()
    assert r._validate(Path("/tmp")) == ["bad"]


def test_override_validate_skips_default_child_walk():
    Requirement.reset()

    class Leaf(Requirement):
        def validate(self, product: Path) -> list[str]:
            return ["leaf"]

    class Parent(Requirement):
        def _validate(self, product: Path, *, survive_exceptions: bool = True) -> list[str]:
            return ["custom"]

    parent = Parent()
    Leaf(parent=parent)
    assert parent._validate(Path("/tmp"), survive_exceptions=True) == ["custom"]


def test_survive_exceptions_records_traceback():
    Requirement.reset()

    class Boom(Requirement):
        def validate(self, product: Path) -> list[str]:
            raise ValueError("nope")

    b = Boom()
    issues = b._validate(Path("/tmp"), survive_exceptions=True)
    assert len(issues) == 1
    assert "exception at" in issues[0]
    assert "ValueError: nope" in issues[0]
    assert "Traceback (most recent call last)" in issues[0]


def test_survive_exceptions_false_propagates():
    Requirement.reset()

    class Boom(Requirement):
        def validate(self, product: Path) -> list[str]:
            raise RuntimeError("boom")

    b = Boom()
    with pytest.raises(RuntimeError, match="boom"):
        b._validate(Path("/tmp"), survive_exceptions=False)


def test_to_dict_includes_config_and_nested_children():
    Requirement.reset()

    class Cfg(BaseModel):
        name: str
        port: int = 9

    class Leaf(Requirement):
        pass

    class Root(Requirement[Cfg]):
        pass

    root = Root(config=Cfg(name="svc", port=80))
    Leaf(parent=root)

    d = root.to_dict()
    assert d["config"] == {"name": "svc", "port": 80}
    assert d["class"].endswith("Root")
    assert len(d["children"]) == 1
    assert d["children"][0]["class"].endswith("Leaf")
    assert "config" not in d["children"][0]

    roots = Requirement.export_roots()
    assert len(roots) == 1
    assert roots[0] == d


def test_validate_reads_config():
    Requirement.reset()

    class Cfg(BaseModel):
        env: str

    class R(Requirement[Cfg]):
        def validate(self, product: Path) -> list[str]:
            if self.config is None or self.config.env != "prod":
                return ["wrong env"]
            return []

    r = R(config=Cfg(env="prod"))
    assert r._validate(Path("/tmp")) == []


def test_three_level_validate_order():
    Requirement.reset()
    order: list[str] = []

    class L3(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("l3")
            return []

    class L2(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("l2")
            return []

    class L1(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("l1")
            return []

    l1 = L1()
    l2 = L2(parent=l1)
    L3(parent=l2)

    l1._validate(Path("/tmp"))
    assert order == ["l3", "l2", "l1"]


def test_mixed_child_issues_parent_still_runs_all_children():
    Requirement.reset()
    order: list[str] = []

    class Bad(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("bad")
            return ["from-bad"]

    class Ok(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("ok")
            return []

    class Parent(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("parent")
            return []

    p = Parent()
    Bad(parent=p)
    Ok(parent=p)

    issues = p._validate(Path("/tmp"), survive_exceptions=True)
    assert order == ["bad", "ok", "parent"]
    assert issues == ["from-bad"]


def test_mixed_child_raise_sibling_and_parent_still_run():
    Requirement.reset()
    order: list[str] = []

    class Boom(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("boom")
            raise RuntimeError("child boom")

    class Ok(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("ok")
            return []

    class Parent(Requirement):
        def validate(self, product: Path) -> list[str]:
            order.append("parent")
            return []

    p = Parent()
    Boom(parent=p)
    Ok(parent=p)

    issues = p._validate(Path("/tmp"), survive_exceptions=True)
    assert order == ["boom", "ok", "parent"]
    assert len(issues) == 1
    assert "RuntimeError: child boom" in issues[0]
    assert "Traceback" in issues[0]


def test_multi_root_export_roots():
    Requirement.reset()

    class A(Requirement):
        pass

    class B(Requirement):
        pass

    A()
    B()
    roots = Requirement.export_roots()
    assert len(roots) == 2
    classes = {r["class"].split(".")[-1] for r in roots}
    assert classes == {"A", "B"}
