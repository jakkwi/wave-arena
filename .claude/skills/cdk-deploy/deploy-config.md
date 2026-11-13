# Deploy config

| Setting | Value |
|---|---|
| CDK app | `infra/app.py` (run from `infra/`) |
| Stack name | `WaveArenaStack` |
| Region | `eu-central-1` (Frankfurt), change here if needed |
| AWS profile | from the user's shell (`AWS_PROFILE`), see CLAUDE.local.md |
| CDK CLI | pinned in `infra/package.json`, run with `npx cdk` |
| Approval | `--require-approval broadening` |
| Budget | 5 USD monthly, email alert |
