# infra/ (AWS CDK, Python)

The CDK app for the Wave Arena backend. `WaveArenaStack` holds the leaderboard table, the raw events bucket and the two Lambda functions with hand-written least-privilege policies ([ADR 0005](../docs/adr/0005-cdk-stack-data-and-iam.md)). In front of them sits the public HTTP API with stage throttling, and a 5 USD monthly budget alert ([ADR 0006](../docs/adr/0006-http-api-throttling-budget.md)).

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `wave_arena_infra/stack.py` | `WaveArenaStack` |
| `wave_arena_infra/api.py` | HTTP API, routes, `$default` stage throttling |
| `wave_arena_infra/budget.py` | Monthly cost budget and the `BudgetEmail` parameter |
| `tests/` | `aws_cdk.assertions` tests (exact IAM statements, bucket and table settings, code asset contents, routes, throttling, invoke permissions, budget) |
| `package.json` | Pinned CDK CLI, run with `npx --no-install cdk` |

```bash
uv sync --extra dev --extra infra   # from the repo root
cd infra
npm ci
npx --no-install cdk synth   # --no-install: fail instead of fetching an unpinned CLI
npx --no-install cdk diff     # needs an AWS session
```

The budget alert address is the `BudgetEmail` stack parameter, never a file in the repo. Keep it in an environment variable and pass it on the first deploy: `--parameters BudgetEmail=$WAVE_ARENA_BUDGET_EMAIL` (later deploys reuse it). The API base URL is the stack output `ApiUrl`.

Deploying: only through the `cdk-deploy` skill checklist (synth, diff, security-auditor, explicit yes). `cdk destroy` is run by hand, never by Claude.
