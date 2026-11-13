# 0003: Serverless backend, DynamoDB leaderboard, S3 raw events

**Status:** Accepted

## Context
The game needs a leaderboard (small, read often, ordered by score) and raw run events for analytics (append only, read in batch). Cost must stay at about zero.

## Decision
- API Gateway HTTP API + Lambda (Python 3.12) + DynamoDB on-demand for the leaderboard.
- S3 for raw run events as JSON objects, partitioned by date, read by `analytics/`.
- Infrastructure in AWS CDK (Python). AWS Budget alert at 5 USD.

## Consequences
- Free tier covers the expected traffic. No servers to patch.
- Top N from DynamoDB needs a deliberate key design (decided in M4).
- Cold starts are acceptable for a game score screen.
