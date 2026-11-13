# Git and GitHub

- One branch per issue: `issue-<n>-<short-name>`, or `m<k>-<short-name>` for milestone setup work. PR title = issue title, body starts with `Closes #<n>`.
- Small commits, imperative subject line in English, under 72 characters.
- Author is Jakub Kwiatkowski. Never add Co-Authored-By trailers or any mention of Claude or AI in commits, PRs, code or docs.
- Never force push, never rewrite main.
- Never commit O3DE build output (`game/build/`, `game/Cache/`, `game/user/`), `cdk.out/`, `.venv/` or `node_modules/`.
- Large binary assets (textures, meshes, audio) go through Git LFS; ask before adding any file over 5 MB.
- Before opening a PR: tests green, ruff, mypy and lint-imports clean, ROADMAP checkboxes and docs updated if behaviour changed.
