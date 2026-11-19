# 0005: CDK stack: removal policies, event lifecycle, hand-written IAM

**Status:** Accepted

## Context
Issue #11 builds the data layer of `WaveArenaStack`: the leaderboard table, the raw events bucket and the two Lambda functions. Three choices in it are easy to get wrong silently: what happens to data on `cdk destroy`, how long raw events live, and how wide the Lambda permissions are.

## Decision

**Removal policies.**

| Resource | Policy | Why |
|---|---|---|
| DynamoDB table | `DESTROY` | An index of the S3 events (ADR 0004). PITR is off for the same reason |
| S3 bucket | `RETAIN` | The raw events are the source of truth. No `auto_delete_objects`: it adds a helper Lambda with delete rights |
| Log groups | `DESTROY` | Debug output only, 30 days retention |

**Event lifecycle.** Objects under `runs/` expire after 730 days; incomplete multipart uploads are aborted after 1 day. No storage class transitions: events are a few hundred bytes, and Standard-IA and Glacier Instant Retrieval bill at least 128 KB per object, so a transition would cost more than it saves.

**Functions.** Python 3.12 on ARM64 (Graviton): about 20 percent cheaper per GB-second, and the code is pure Python plus the runtime's boto3, so there are no native wheels to build for a second architecture. 10 s timeout, 256 MB memory.

**Encryption.** SSE-S3 (`AES256`), not a customer managed KMS key: no key cost, and the Lambda needs no `kms:*` permission. ACLs are disabled (`BucketOwnerEnforced`), all public access blocked, a bucket policy denies any request without TLS or with TLS below 1.2.

**Code asset.** The repo root filtered to `backend/**/*.py` without `backend/tests`: the handlers import `backend.*` as in tests, and no non-Python file left in `backend/` can be deployed. boto3 comes from the Lambda runtime.

**IAM: hand-written statements, not grants.** CDK grants are wider than the code needs:

| Grant | Adds beyond what the code calls |
|---|---|
| `table.grant_write_data` | `BatchWriteItem`, `UpdateItem`, `DeleteItem`, `DescribeTable` |
| `table.grant_read_data` | `GetItem`, `BatchGetItem`, `Scan`, `DescribeTable`, stream reads |
| `bucket.grant_put` | `s3:Abort*`, `PutObjectLegalHold`, `PutObjectRetention`, tagging and version ACLs |
| `AWSLambdaBasicExecutionRole` | `logs:CreateLogGroup` and log writes on `Resource "*"` |

Each function gets its own role with only:

| Function | Action | Resource |
|---|---|---|
| `post_run` | `dynamodb:PutItem` | the table |
| `post_run` | `s3:PutObject` | `<bucket>/runs/*` |
| `get_leaderboard` | `dynamodb:Query` | the table |
| both | `logs:CreateLogStream`, `logs:PutLogEvents` | the function's own log group |

The log groups are created by the stack, so the roles need no `logs:CreateLogGroup` and no log-retention helper Lambda is deployed.

## Consequences
- A new adapter call (for example `UpdateItem`) fails with `AccessDenied` until the statement is added. The infra tests pin the exact statements, so that change is visible in review.
- After 730 days an event is gone from S3 but its leaderboard row stays in DynamoDB. A rebuild from S3 (ADR 0004) then covers only the last two years. Accepted for a learning project: two years of rebuildable history is enough, and losing the table is unlikely. If older runs must survive a table loss, drop the expiration or turn PITR on.
- `cdk destroy` leaves the bucket behind; deleting it is a manual step.
