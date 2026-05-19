"""specreq CLI."""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path
from typing import Annotated

import typer
from specreq import load_spec

app = typer.Typer()


def _load_reqs(reqs_dir: Path) -> None:
    """Import all Python files under reqs/ so Req subclasses auto-register."""
    if not reqs_dir.is_dir():
        # Will surface later as "Registered: (none)" which is clear enough.
        # Don't error here — some projects may have reqs baked into specreq itself.
        return
    reqs_str = str(reqs_dir.resolve())
    if reqs_str not in sys.path:
        sys.path.insert(0, reqs_str)
    for py_file in sorted(reqs_dir.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        # Convert reqs/sub/pkg.py -> sub.pkg
        rel = py_file.relative_to(reqs_dir)
        module = str(rel.with_suffix("")).replace("/", ".")
        # NOTE: reload only happens in tests (multiple invokes per process).
        # In production a module is imported once; reload is a no-op.
        if module in sys.modules:
            importlib.reload(sys.modules[module])
        else:
            importlib.import_module(module)


def _resolve_spec(spec: str | None) -> Path:
    """Find the spec file: explicit path, or single file in specs/."""
    if spec is not None:
        p = Path(spec)
        if not p.exists():
            typer.echo(f"Spec file not found: {p}")
            raise typer.Exit(1)
        return p
    specs_dir = Path("specs")
    if not specs_dir.is_dir():
        typer.echo("No specs/ directory found.")
        raise typer.Exit(1)
    json_files = list(specs_dir.glob("*.json"))
    if len(json_files) == 0:
        typer.echo("No .json files found in specs/.")
        raise typer.Exit(1)
    if len(json_files) > 1:
        typer.echo(f"Multiple specs found in specs/, specify one: {[f.name for f in json_files]}")
        raise typer.Exit(1)
    return json_files[0]


def _resolve_product(product: str | None) -> Path:
    """Find the product dir: explicit path, or single dir in products/."""
    if product is not None:
        p = Path(product).resolve()
        if not p.exists():
            typer.echo(f"Product path does not exist: {p}")
            raise typer.Exit(1)
        return p
    products_dir = Path("products")
    if not products_dir.is_dir():
        typer.echo("No products/ directory found.")
        raise typer.Exit(1)
    dirs = [d for d in products_dir.iterdir() if d.is_dir()]
    if len(dirs) == 0:
        typer.echo("No directories found in products/.")
        raise typer.Exit(1)
    if len(dirs) > 1:
        typer.echo(f"Multiple products found, specify one: {[d.name for d in dirs]}")
        raise typer.Exit(1)
    return dirs[0].resolve()


@app.command()
def validate(
    spec: Annotated[str | None, typer.Argument(help="Spec JSON file (default: auto-detect from specs/)")] = None,
    product: Annotated[str | None, typer.Argument(help="Product directory (default: auto-detect from products/)")] = None,
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Propagate validator exceptions instead of catching per-node",
    ),
):
    """Validate a product against a spec."""
    _load_reqs(Path("reqs"))

    spec_path = _resolve_spec(spec)
    try:
        roots = load_spec(spec_path)
    except Exception as e:
        typer.echo(f"Failed to load spec: {e}")
        raise typer.Exit(1)

    product_path = _resolve_product(product)

    survive = not strict
    issues: list[str] = []
    for root in roots:
        tag = f"{root.__class__.__module__}.{root.__class__.__qualname__}"
        try:
            lines = root._validate(product_path, survive_exceptions=survive)
            issues.extend(f"[root {tag}] {line}" for line in lines)
        except Exception as e:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            issues.append(
                f"[root {tag}] exception escaped _validate tree: "
                f"{type(e).__name__}: {e}\n{tb}"
            )

    if issues:
        typer.echo(f"Issues ({len(issues)}):")
        for i in issues:
            typer.echo(f"  - {i}")
        raise typer.Exit(1)

    typer.echo(f"Valid. {len(roots)} root(s) passed.")


if __name__ == "__main__":
    app()
