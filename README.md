# Wave Arena

A small top-down wave survival game built in [O3DE](https://www.o3de.org/) with a serverless AWS backend for the leaderboard and run telemetry. It is a learning project: every part of the stack has one concrete job.

```
 O3DE game (C++ Gem)                      AWS (CDK, Python)
 +-------------------------+   HTTPS   +---------------------------------+
 | Player, waves, enemies  | --------> | API Gateway (HTTP API)          |
 | HP, score, LyShine UI   |  POST     |   POST /runs   GET /leaderboard |
 | HttpRequestor Gem       | <-------- |          |                      |
 +-------------------------+  top 10   |      Lambda (Python, thin)      |
            ^                          |          |                      |
            | arena.json               |   domain (pure Python)          |
 +-------------------------+           |      /             \            |
 | Editor Python script    |           | DynamoDB          S3            |
 | builds arena + spawners |           | (leaderboard)     (raw events)  |
 +-------------------------+           +---------------------------------+
                                                         |
                                           analytics/ (death heatmap)
                                                         |
                                           wave balance config change
```

| Tech | Role |
|---|---|
| C++ | Project Gem: `WaveSpawnerComponent`, `HealthComponent`, chase and attack AI, communication over EBus |
| O3DE | Level, prefabs, input, top-down camera, LyShine score UI |
| Python | Editor scripts that build the arena from JSON, Lambda backend, analytics |
| AWS | API Gateway, Lambda, DynamoDB leaderboard, S3 raw run events, budget alert, all in CDK |
| Game dev | Game loop, wave balance, telemetry for difficulty tuning (where players die most) |

## Repository layout

```
wave-arena/
  game/                   O3DE project (created in M0)
  tools/editor_scripts/   Python for the O3DE Editor
  backend/
    domain/               logic without AWS dependencies
    adapters/             DynamoDB, S3
    lambdas/              thin handlers
    tests/                pytest + moto
  infra/                  AWS CDK (Python)
  analytics/              heatmaps, reports
  docs/                   ROADMAP, ADRs, learning notes
  .claude/                Claude Code setup (rules, commands, agents, hooks, skills)
  .github/                CI, Dependabot, templates
```

## Getting started

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 22+ (only for the CDK CLI), Git. For the game: Visual Studio 2022 with the C++ workload, CMake, O3DE (see [game/README.md](game/README.md)).

```bash
uv sync --extra dev --extra infra
uv run pytest -q
uv run ruff check .
uv run mypy
uv run lint-imports
```

CDK (no AWS account needed for synth):

```bash
cd infra
npm ci
npx cdk synth
```

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Milestones M0 to M6, each one a separate, working step.

## What I learned

One line per lesson, with a link to the commit or PR that shows it. Filled in as the milestones close.

| Milestone | Lesson | Commit / PR |
|---|---|---|
| M0 | | |
| M1 | | |
| M2 | | |
| M3 | | |
| M4 | | |
| M5 | | |
| M6 | | |

## License

Not decided yet. All rights reserved until a license file is added.
