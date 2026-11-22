# Architecture decision records

One file per significant decision: `NNNN-short-title.md` with Status, Context, Decision, Consequences.

| ADR | Decision |
|---|---|
| [0001](0001-hexagonal-backend.md) | Hexagonal architecture for the backend |
| [0002](0002-gameplay-in-cpp-gem.md) | Gameplay in a C++ project Gem, tools in Python |
| [0003](0003-serverless-telemetry.md) | Serverless backend, DynamoDB leaderboard, S3 raw events |
| [0004](0004-dynamodb-leaderboard-keys.md) | DynamoDB leaderboard keys: one board partition, rank-ordered sort key |
| [0005](0005-cdk-stack-data-and-iam.md) | CDK stack: removal policies, event lifecycle, hand-written IAM |
| [0006](0006-http-api-throttling-budget.md) | Public HTTP API: throttling, no CORS, body size, 5 USD budget |
