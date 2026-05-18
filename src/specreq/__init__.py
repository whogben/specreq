"""specreq — write product specs as Python code."""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import TypeVar, Generic

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Requirement(Generic[T]):
    """Subclass to define a reusable spec element. Create instances to build a spec tree."""

    _instances: list[Requirement] = []

    def __init__(self, config: T | None = None, parent: Requirement | None = None):
        self.config = config
        self.parent = parent
        self.children: list[Requirement] = []
        if parent is not None:
            parent.children.append(self)
        Requirement._instances.append(self)

    @staticmethod
    def _format_node_exception(node: Requirement, exc: BaseException) -> str:
        fqn = f"{node.__class__.__module__}.{node.__class__.__qualname__}"
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return f"exception at {fqn}: {type(exc).__name__}: {exc}\n{tb}"

    def _validate(self, product: Path, *, survive_exceptions: bool = True) -> list[str]:
        """Run ``_validate`` on each child, then ``validate`` on this node.

        Override this when you need to choose which children validate or in what order.
        Forward ``survive_exceptions`` if you call ``super()._validate`` from a subclass.

        When ``survive_exceptions`` is True (default), child failures are recorded with a
        full traceback string and validation continues. When False, the first exception
        propagates (``validate`` is never wrapped — only this orchestration).
        """
        issues: list[str] = []
        for child in self.children:
            if survive_exceptions:
                try:
                    issues.extend(
                        child._validate(
                            product, survive_exceptions=survive_exceptions
                        )
                    )
                except Exception as e:
                    issues.append(self._format_node_exception(child, e))
            else:
                issues.extend(
                    child._validate(
                        product, survive_exceptions=survive_exceptions
                    )
                )
        if survive_exceptions:
            try:
                issues.extend(self.validate(product))
            except Exception as e:
                issues.append(self._format_node_exception(self, e))
        else:
            issues.extend(self.validate(product))
        return issues

    def validate(self, product: Path) -> list[str]:
        """Return issues for this node only. Children are handled by ``_validate``."""
        return []

    def to_dict(self) -> dict:
        d: dict = {
            "class": f"{self.__class__.__module__}.{self.__class__.__qualname__}",
        }
        if self.config is not None:
            d["config"] = self.config.model_dump()
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def export_roots(cls) -> list[dict]:
        """Serialize all root instances (no parent) as a list of dicts."""
        return [i.to_dict() for i in cls._instances if i.parent is None]

    @classmethod
    def reset(cls):
        cls._instances.clear()


__all__ = ["Requirement"]
