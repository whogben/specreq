# specreq

Write product specs as Python code.

See the [Changelog](https://github.com/whogben/specreq/blob/main/CHANGELOG.md) for recent changes.
1. Define reusable elements by subclassing `Requirement` — override `validate(self, product: Path)` for each node, or `_validate` to control how children are validated.
2. Instance reusable elements to create specific product specs.
3. Run `specreq <spec> <product> [--save] [--strict]` — `--save` writes the requirement tree as JSON; `--strict` turns off exception catching inside `_validate` (fail fast). Default collects exceptions with tracebacks.
