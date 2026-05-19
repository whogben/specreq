# specreq

Define reusable requirements as typed Pydantic models. Compose them into specs as JSON trees. Validate products against them.

See the [Changelog](https://github.com/whogben/specreq/blob/main/CHANGELOG.md) for recent changes.

```
my_project/
  reqs/          # req definitions — gather shared ones, write custom ones
  specs/         # specs — JSON trees of configured req instances
  products/      # built output that specreq validates against your specs
```

1. **Gather reqs** — collect shared requirements and write custom ones by subclassing `Req` with typed fields, a `kind` discriminator, and a `validate(self, product: Path)` method.
2. **Write specs** — compose specs as JSON trees of configured req instances describing what your product should satisfy.
3. **Build, validate, repeat** — run `specreq validate` from the project root.

Req files under `reqs/` are standard Python — flat files are modules, directories with `__init__.py` are packages. Reqs import each other normally.
