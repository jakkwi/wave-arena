# infra/ (AWS CDK, Python)

The CDK app for the Wave Arena backend. `WaveArenaStack` holds the leaderboard table, the raw events bucket and the two Lambda functions with hand-written least-privilege policies ([ADR 0005](../docs/adr/0005-cdk-stack-data-and-iam.md)). The HTTP API and the budget alert follow in issue #12.

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `wave_arena_infra/stack.py` | `WaveArenaStack` |
| `tests/` | `aws_cdk.assertions` tests (exact IAM statements, bucket and table settings, code asset contents) |
| `package.json` | Pinned CDK CLI, run with `npx --no-install cdk` |

```bash
uv sync --extra dev --extra infra   # from the repo root
cd infra
npm ci
npx --no-install cdk synth   # --no-install: fail instead of fetching an unpinned CLI
npx --no-install cdk diff     # needs an AWS session
```

Deploying: only through the `cdk-deploy` skill checklist (synth, diff, security-auditor, explicit yes). `cdk destroy` is run by hand, never by Claude.
