---
name: cdk-deploy
description: Use when the user asks to deploy, diff or bootstrap the AWS CDK stack in infra/, or to check what a deploy would change. Never deploy on your own initiative.
---
# Deploying the CDK stack safely

Only run a deploy when the user asked for it in chat in this conversation. Config for this checklist: [deploy-config.md](deploy-config.md).

1. Preconditions
   - Working tree clean, on the branch the user named (normally main after merge).
   - `uv run pytest -q` and `uv run lint-imports` green.
   - The user has an active AWS session in their shell (`AWS_PROFILE` set, SSO logged in). Never read `~/.aws` and never ask for keys.
2. Synth and diff
   - `cd infra && npm ci && npx cdk synth` then `npx cdk diff`.
   - Summarise the diff for the user: new or replaced resources, IAM changes (each statement), security group or bucket policy changes, anything with a replacement or deletion.
3. Security check
   - First deploy, or any IAM, S3 policy or API change: run the security-auditor agent on the diff. Blocking or Critical findings stop the deploy.
   - Confirm the budget alert is still in the stack.
4. Bootstrap (first time per account and region only)
   - Explain what `cdk bootstrap` creates (staging bucket, roles) and ask before running it.
5. Deploy
   - Ask the user for a final yes, then `npx cdk deploy --require-approval broadening`. The user approves IAM broadening in the prompt themselves.
6. After deploy
   - Print the stack outputs (API URL). Suggest a smoke test with the user running it.
   - Record the date, what was deployed and the cost check in `docs/learning/M4.md` (or the current milestone note).

Never run `cdk destroy` (blocked by a hook). If the user wants to tear down, give them the command to run themselves.
