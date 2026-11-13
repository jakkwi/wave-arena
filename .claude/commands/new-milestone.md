---
description: Open a milestone from docs/ROADMAP.md (issues, learning note, branch)
argument-hint: <M0..M6>
---
Open milestone $ARGUMENTS.

1. Read the $ARGUMENTS section of docs/ROADMAP.md. Check that the previous milestone's acceptance criteria are all ticked; if not, list what is missing and ask whether to continue.
2. Before anything else, explain in a short briefing: what this milestone builds, the concepts to learn (from "What to learn"), and the official docs to read first.
3. Propose a split into GitHub issues: one issue per acceptance criterion or small group of them. Each issue: title, short description, acceptance criteria as checkboxes, label `$ARGUMENTS`. Show the list and wait for the user to confirm before creating anything.
4. After confirmation: create the GitHub milestone if it does not exist (`gh api repos/{owner}/{repo}/milestones`), then the issues with `gh issue create --milestone`.
5. Copy `docs/learning/TEMPLATE.md` to `docs/learning/$ARGUMENTS.md` and fill in the title.
6. Update the status column in the ROADMAP table to "In progress".
7. Create branch `m<n>-kickoff` with the doc changes and report the issue numbers in suggested order.
