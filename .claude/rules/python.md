---
paths:
  - "backend/**/*.py"
  - "infra/**/*.py"
  - "tools/**/*.py"
  - "analytics/**/*.py"
  - "tests/**/*.py"
---
# Python rules

- Python 3.12. Type hints everywhere; `mypy --strict` must pass.
- Ruff for lint and format, line length 100. Run `uv run ruff check .` and `uv run ruff format .`.
- Dataclasses (`frozen=True`) or `TypedDict` for data crossing module boundaries. No untyped dicts in the domain.
- Use `logging` (or Powertools Logger in Lambdas if added), never `print` in backend code. Never log full request bodies or secrets.
- boto3 clients are created once per Lambda container (module level in the handler module) and injected into adapters.
- Lambda handler signature: `def handler(event: dict[str, Any], context: object) -> dict[str, Any]`.
- `pathlib` for paths, no hard-coded `/` or `\\` separators: the dev machine is Windows, CI is Linux.
- Editor scripts (`tools/editor_scripts/`): only the thin O3DE part imports `azlmbr`. Parsing and validation live in plain modules that pytest can import.
- Dependencies are managed with uv. Add one with `uv add` only after the user agrees.
