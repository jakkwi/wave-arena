# 0004: DynamoDB leaderboard keys: one board partition, rank-ordered sort key

**Status:** Accepted

## Context
`GET /leaderboard` returns the top 10 runs (docs/api.md). In DynamoDB the access pattern drives the key design: `Scan` reads and bills every item, so the top N must come from a `Query` that reads only N items, already in rank order.

The domain ranks runs by: higher score, then more waves, then earlier submission, then `run_id` (`backend/domain/use_cases.py`, `ranking_key`).

Options considered:

| Option | Keys | Top 10 | Cost and trade-offs |
|---|---|---|---|
| A (chosen) | PK `board`, SK `rank_key` (string encoding the ranking) | `Query` on one partition, ascending, `Limit 10` | One table, no index, one write per run. All writes hit one partition |
| B | PK `run_id`, GSI on `board` + numeric `score` | `Query` on the GSI | Second copy of the data and a second write. Same hot partition, now in the GSI. Ties need code |
| C | PK `run_id` only | `Scan` and sort | Cost grows with every run. Rejected |

## Decision
Option A.

- Partition key `board` (string). Always `"global"` for now. Per-arena boards later can use the arena name with no schema change.
- Sort key `rank_key` (string), fixed width so that string order equals rank order:

  ```
  {MAX_SCORE - score:08d}#{MAX_WAVES - waves_survived:04d}#{received_at UTC, microseconds}Z#{run_id}
  ```

  Inverting score and waves makes an ascending sort return the best run first. The timestamp breaks ties in favour of the earlier run, `run_id` makes every key unique.
- Top N is `Query(board = "global", ScanIndexForward = true, Limit = N)`.
- The domain still sorts what the adapter returns (cheap for 10 items), so ranking stays a domain rule and the adapter cannot silently break it. A test checks that `rank_key` order equals `ranking_key` order.
- Billing mode on-demand.
- Point-in-time recovery: **off**. Every valid run is archived in S3 before it is saved to DynamoDB (docs/api.md), so the leaderboard can be rebuilt from S3. Turn PITR on if the table ever holds data that is not in S3.

## Consequences
- Top 10 costs one `Query` that reads 10 items, whatever the table size.
- One partition takes all writes. A DynamoDB partition handles about 1000 writes per second; the game sends a few per minute. If that ever matters, shard the board (`global#0` to `global#9`) and merge the shards' top N in the domain.
- `MAX_SCORE` and `MAX_WAVES` are part of the key format. Raising them past their digit width changes every key: that needs a new board name and a backfill from S3.
- The table grows forever. Fine at this scale; add a TTL or periodic cleanup if storage cost ever shows up in the budget.
