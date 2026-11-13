---
paths:
  - "backend/**"
  - "tools/**"
  - "analytics/**"
  - "infra/**"
  - "tests/**"
  - "game/Gem/**"
---
# Testing

- Backend is test-first: write the failing test, then the code. Start with the domain, then adapters, then handlers, then infra.
- pytest. Backend tests live in `backend/tests/` and mirror the package: `backend/domain/run.py` -> `backend/tests/domain/test_run.py`.
- Domain tests use plain objects and in-memory fakes of the ports, no moto.
- Adapter tests use moto (`mock_aws`) with fake credentials set in a fixture. Never touch a real AWS account in tests.
- Handler tests build API Gateway HTTP API (payload v2) events and assert status codes and bodies.
- Infra tests use `aws_cdk.assertions.Template` to check IAM policies, bucket settings and the budget.
- Every acceptance criterion in docs/ROADMAP.md that can be automated gets at least one test.
- Security rules (input validation, size limits, least privilege) have explicit tests.
- C++: pure logic tested with AzTest in `game/Gem/Tests/`, run locally (CI does not build the engine).
- Before every commit: `uv run ruff check .`, `uv run mypy`, `uv run pytest -q`, `uv run lint-imports`.
