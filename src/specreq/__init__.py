"""specreq — define requirements as typed models, compose specs as JSON, validate products."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_REQ_REGISTRY: dict[str, type[Req]] = {}


class Req(BaseModel):
    """Base requirement. Subclass with typed fields and a kind discriminator."""

    kind: str
    children: list[Req] = []

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        if "kind" in cls.model_fields:
            default = cls.model_fields["kind"].default
            if isinstance(default, str):
                _REQ_REGISTRY[default] = cls

    def _format_node_exception(self, exc: BaseException) -> str:
        fqn = f"{type(self).__module__}.{type(self).__qualname__}"
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return f"exception at {fqn}: {type(exc).__name__}: {exc}\n{tb}"

    def _validate(self, product: Path, *, survive_exceptions: bool = True) -> list[str]:
        """Validate children first, then self. Override to customize orchestration."""
        issues: list[str] = []
        for child in self.children:
            if survive_exceptions:
                try:
                    issues.extend(
                        child._validate(product, survive_exceptions=survive_exceptions)
                    )
                except Exception as e:
                    issues.append(child._format_node_exception(e))
            else:
                issues.extend(
                    child._validate(product, survive_exceptions=survive_exceptions)
                )
        if survive_exceptions:
            try:
                issues.extend(self.validate(product))
            except Exception as e:
                issues.append(self._format_node_exception(e))
        else:
            issues.extend(self.validate(product))
        return issues

    def validate(self, product: Path) -> list[str]:
        """Return issues for this node only. Children are handled by _validate."""
        return []

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize with children preserving their actual subclass fields."""
        exclude: set[str] = kwargs.pop("exclude", None) or set()
        data = super().model_dump(exclude=exclude | {"children"}, **kwargs)
        data["children"] = [c.model_dump(exclude=exclude, **kwargs) for c in self.children]
        return data


Req.model_rebuild()


def load_spec(source: Path | str | dict | list) -> list[Req]:
    """Load specs from a JSON file path, dict, or list of dicts. Always returns a list."""
    if isinstance(source, list):
        return [_deserialize_req(item) for item in source]
    if isinstance(source, dict):
        data = source
    else:
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(f"Spec file not found: {p}")
        data = json.loads(p.read_text())

    if isinstance(data, list):
        return [_deserialize_req(item) for item in data]
    return [_deserialize_req(data)]


def _deserialize_req(data: dict) -> Req:
    kind = data.get("kind")
    if kind not in _REQ_REGISTRY:
        registered = ", ".join(sorted(_REQ_REGISTRY)) or "(none)"
        raise ValueError(f"Unknown req kind: {kind!r}. Registered: {registered}")
    cls = _REQ_REGISTRY[kind]
    children = [_deserialize_req(c) for c in data.get("children", [])]
    fields = {k: v for k, v in data.items() if k != "children"}
    return cls(**fields, children=children)


__all__ = ["Req", "load_spec"]
