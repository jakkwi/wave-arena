# infra/ (AWS CDK, Python)

The CDK app for the Wave Arena backend. Empty stack until M4.

| File | Purpose |
|---|---|
| `app.py` | CDK entry point |
| `wave_arena_infra/stack.py` | `WaveArenaStack` |
| `tests/` | `aws_cdk.assertions` tests (IAM, bucket settings, budget) |
| `package.json` | Pinned CDK CLI, run with `npx cdk` |

```bash
uv sync --extra dev --extra infra   # from the repo root
cd infra
npm ci
npx cdk synth
npx cdk diff     # needs an AWS session
```

Deploying: only through the `cdk-deploy` skill checklist (synth, diff, security-auditor, explicit yes). `cdk destroy` is run by hand, never by Claude.
