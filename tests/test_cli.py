import json
from pathlib import Path

from typer.testing import CliRunner

from specreq.cli import app

runner = CliRunner()

SPEC_PY = '''\
from specreq import Requirement


class Root(Requirement):
    pass


Root()
'''

SPEC_NO_INSTANCES = """\
from specreq import Requirement


class Root(Requirement):
    pass
"""

SPEC_ERROR = '''\
from pathlib import Path

from specreq import Requirement


class Root(Requirement):
    def validate(self, product: Path) -> list[str]:
        raise ValueError("spec boom")


Root()
'''

SPEC_TWO_ROOTS = '''\
from specreq import Requirement


class A(Requirement):
    pass


class B(Requirement):
    pass


A()
B()
'''


def _write_spec(tmp: Path, filename: str, content: str) -> Path:
    p = tmp / filename
    p.write_text(content)
    return p


def test_validate_file_spec(tmp_path):
    spec = _write_spec(tmp_path, "file_spec.py", SPEC_PY)
    result = runner.invoke(app, [str(spec), str(tmp_path)])
    assert result.exit_code == 0
    assert "Valid." in result.stdout


def test_validate_twice_same_process_reloads_spec(tmp_path):
    """Second invoke must rebuild instances after reset (sys.modules cache)."""
    spec = _write_spec(tmp_path, "reload_spec.py", SPEC_PY)
    for _ in range(2):
        result = runner.invoke(app, [str(spec), str(tmp_path)])
        assert result.exit_code == 0, result.stdout
        assert "Valid." in result.stdout


def test_validate_no_instances(tmp_path):
    spec = _write_spec(tmp_path, "empty_spec.py", SPEC_NO_INSTANCES)
    result = runner.invoke(app, [str(spec), str(tmp_path)])
    assert result.exit_code == 1
    assert "No Requirement instances" in result.stdout


def test_validate_missing_product(tmp_path):
    spec = _write_spec(tmp_path, "prod_spec.py", SPEC_PY)
    missing = tmp_path / "nope"
    result = runner.invoke(app, [str(spec), str(missing)])
    assert result.exit_code == 1
    assert "Product path does not exist" in result.stdout


def test_validate_missing_spec_module(tmp_path):
    result = runner.invoke(
        app, ["not_a_real_module_xyz_abc", str(tmp_path)]
    )
    assert result.exit_code == 1
    assert "Could not import spec" in result.stdout


def test_validate_survive_includes_traceback(tmp_path):
    spec = _write_spec(tmp_path, "boom_spec.py", SPEC_ERROR)
    result = runner.invoke(app, [str(spec), str(tmp_path)])
    assert result.exit_code == 1
    assert "Traceback (most recent call last)" in result.stdout
    assert "exception at" in result.stdout


def test_validate_strict_propagates(tmp_path):
    spec = _write_spec(tmp_path, "strict_spec.py", SPEC_ERROR)
    result = runner.invoke(app, [str(spec), str(tmp_path), "--strict"])
    assert result.exit_code == 1
    assert result.exception is not None


def test_validate_two_roots(tmp_path):
    spec = _write_spec(tmp_path, "two_roots.py", SPEC_TWO_ROOTS)
    result = runner.invoke(app, [str(spec), str(tmp_path)])
    assert result.exit_code == 0
    assert "2 root(s) passed." in result.stdout


def test_validate_save_writes_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = _write_spec(tmp_path, "save_me.py", SPEC_PY)
    result = runner.invoke(app, [str(spec), str(tmp_path), "--save"])
    assert result.exit_code == 0
    assert "Saved save_me.json" in result.stdout

    out = tmp_path / "save_me.json"
    assert out.is_file()
    data = json.loads(out.read_text())
    assert isinstance(data, list)
    assert len(data) == 1
    assert "class" in data[0]
    assert data[0]["class"].endswith("Root")


def test_validate_save_two_roots_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = _write_spec(tmp_path, "pair_spec.py", SPEC_TWO_ROOTS)
    result = runner.invoke(app, [str(spec), str(tmp_path), "--save"])
    assert result.exit_code == 0
    data = json.loads((tmp_path / "pair_spec.json").read_text())
    assert len(data) == 2
    names = {entry["class"].split(".")[-1] for entry in data}
    assert names == {"A", "B"}
