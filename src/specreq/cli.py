"""specreq CLI."""

from __future__ import annotations

import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Annotated

import typer
from specreq import Requirement

app = typer.Typer()


def _resolve_module_name(target: str) -> str:
    """Top-level module name used by importlib / sys.modules for this target."""
    path = Path(target)
    if path.exists():
        return path.name if path.is_dir() else path.stem
    return target


def _import_target(target: str):
    """Import a module by dotted name or file path. Returns the module."""
    path = Path(target)
    if path.exists():
        # file or dir — add parent to sys.path, import by name
        parent = str(path.parent.resolve())
        if parent not in sys.path:
            sys.path.insert(0, parent)
        if path.is_dir():
            name = path.name
        else:
            name = path.stem
        return importlib.import_module(name)
    else:
        # treat as dotted module name
        return importlib.import_module(target)


def _load_spec(target: str):
    """Load or reload the spec module so import-time instances run after Requirement.reset()."""
    name = _resolve_module_name(target)
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return _import_target(target)


@app.command()
def validate(
    spec: Annotated[str, typer.Argument(help="Spec module: file path or dotted name")],
    product: Annotated[str, typer.Argument(help="Path to the product directory")],
    save: bool = typer.Option(False, "--save", help="Save spec tree as JSON on success"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Propagate validator exceptions (no per-node catch inside _validate)",
    ),
):
    """Validate a product against a spec."""
    Requirement.reset()
    try:
        _load_spec(spec)
    except ModuleNotFoundError as e:
        typer.echo(f"Could not import spec: {e}")
        raise typer.Exit(1)

    instances = Requirement._instances
    if not instances:
        typer.echo("No Requirement instances found in spec.")
        raise typer.Exit(1)

    product_path_obj = Path(product).resolve()
    if not product_path_obj.exists():
        typer.echo(f"Product path does not exist: {product_path_obj}")
        raise typer.Exit(1)

    roots = [i for i in instances if i.parent is None]
    if not roots:
        typer.echo("No root Requirement instances found (every instance has a parent).")
        raise typer.Exit(1)

    survive = not strict
    issues: list[str] = []
    for root in roots:
        tag = f"{root.__class__.__module__}.{root.__class__.__qualname__}"
        try:
            lines = root._validate(
                product_path_obj, survive_exceptions=survive
            )
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

    if save:
        out = Path(f"{Path(spec).stem}.json") if Path(spec).exists() else Path(f"{spec.split('.')[-1]}.json")
        out.write_text(json.dumps(Requirement.export_roots(), indent=2))
        typer.echo(f"Saved {out}")


if __name__ == "__main__":
    app()
