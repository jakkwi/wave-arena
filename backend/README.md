# backend/ (Lambda, hexagonal)

Built test-first in M4. See [ADR 0001](../docs/adr/0001-hexagonal-backend.md).

| Package | Contains | May import |
|---|---|---|
| `domain/` | `Run`, `LeaderboardEntry`, validation, ports (`RunRepository`, `EventArchive`) | only itself |
| `adapters/` | DynamoDB and S3 implementations of the ports | domain, boto3 |
| `lambdas/` | `post_run`, `get_leaderboard` handlers | domain, adapters |
| `tests/` | pytest, moto for adapters, API Gateway v2 events for handlers | everything |

Order of work in M4: domain + tests, then adapters with moto, then handlers, then the CDK stack.
