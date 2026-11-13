# 0001: Hexagonal architecture for the backend

**Status:** Accepted

## Context
The backend is small (two endpoints), but it is a learning project and the logic (run validation, scoring, leaderboard ordering) should be testable without AWS. Lambda handlers that mix parsing, logic and boto3 calls are hard to test and to change.

## Decision
- `backend/domain`: models, rules and ports (`typing.Protocol`). No imports of boto3, botocore or any AWS library.
- `backend/adapters`: DynamoDB and S3 implementations of the ports.
- `backend/lambdas`: thin handlers. Parse the event, build adapters, call the domain, map errors to HTTP codes.
- Enforced by import-linter contracts in pyproject.toml, checked in CI.

## Consequences
- Domain tests are fast and need no mocks; adapter tests use moto.
- A bit more structure than two Lambda files would need. Accepted for the learning value.
