---
paths:
  - "backend/**/*.py"
  - "infra/**/*.py"
  - "game/Gem/**"
---
# Architecture rules

## Backend: hexagonal (ADR 0001)
Dependencies point inward only. Enforced by import-linter (`lint-imports` in CI, contracts in pyproject.toml).

```
lambdas (handlers, wiring)  ->  domain (models, rules, ports)
adapters (dynamodb, s3)     ->  domain
```
- `backend.domain` imports nothing from the project except itself and no AWS library (boto3, botocore, aws_lambda_powertools). Ports are `typing.Protocol`.
- `backend.adapters` implement ports. They never import lambdas or each other.
- `backend.lambdas` are thin: parse the API Gateway event, build adapters, call the domain, map domain errors to HTTP status codes. No business rules in handlers.
- Configuration (table name, bucket name) comes from environment variables read once in the handler module, passed down as arguments.

## API contract
- The run payload and leaderboard response are a versioned contract shared by C++ (M5) and Python. Document it in `docs/api.md` when M4 starts. Breaking changes bump `"v"`.

## Infra
- One CDK stack per environment, resources named by CDK (no hard-coded physical names unless needed).
- Lambda code is packaged from `backend/`; the stack passes resource names to Lambdas through environment variables.
- Use CDK grant methods (`table.grant_read_data(fn)`) where they match least privilege; otherwise write the policy statement by hand and explain it.

## Game (ADR 0002)
- Components communicate through EBus interfaces in `game/Gem/Include/WaveArena/`. No raw pointers between entities.
- Game state (playing, dead, restarting) has one owner component; others listen to its notification bus.
- Balance numbers live in data (reflected fields or wave config files), not in code.
- Keep pure logic (damage rules, wave schedule) in plain C++ classes that do not need an entity, so they can be unit tested.
