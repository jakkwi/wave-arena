---
description: Review the current branch against its issue, the roadmap and project rules
---
Review the changes on the current branch versus main (`git diff main...HEAD`).

- Use the code-reviewer agent for correctness, tests and project rules.
- Use the o3de-expert agent if the diff touches `game/` or `tools/editor_scripts/`.
- Use the security-auditor agent if the diff touches `infra/`, `backend/lambdas/`, IAM, network code, input validation, secrets, CI workflows or dependencies.

Report findings grouped as: Blocking, Should fix, Nice to have. For each: file:line, the problem, a concrete fix. Check that every acceptance criterion of the linked issue and ROADMAP milestone is met. Do not edit files: the user fixes them (learning mode).
