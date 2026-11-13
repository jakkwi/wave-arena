# Roadmap

Seven milestones. Each one ends in something that runs and is merged to main. Do them in order: later milestones assume the earlier ones work.

| # | Milestone | Area | Status |
|---|---|---|---|
| M0 | O3DE setup + project Gem | O3DE, CMake, VS 2022 | Not started |
| M1 | Movement, top-down camera, chasing enemy | C++, EBus | Not started |
| M2 | Waves, HP, death, score screen | C++, LyShine | Not started |
| M3 | Editor script builds the arena from JSON | Python, O3DE Editor | Not started |
| M4 | CDK stack: API, Lambda, DynamoDB, S3, budget | Python, AWS | Not started |
| M5 | Game posts run results and shows top 10 | C++, HTTP, AWS | Not started |
| M6 | Death heatmap and wave rebalancing | Python, game design | Not started |

Each milestone has: goal, acceptance criteria, what to learn, official docs. Learning notes go to `docs/learning/Mn.md` (template in `docs/learning/TEMPLATE.md`), and the best lessons go to the "What I learned" table in README.md.

---

## M0: O3DE setup and project Gem

**Goal.** O3DE installed, an empty project in `game/` builds and opens in the Editor, the project Gem exists.

Plan a separate evening: the first engine build takes a long time and needs a lot of disk space.

**Acceptance criteria**
- [ ] Visual Studio 2022 (Desktop development with C++), CMake and O3DE installed, versions written down in `docs/learning/M0.md`
- [ ] `game/` created with `o3de create-project`, project name `WaveArena`
- [ ] Project builds in `profile` configuration and the Editor opens an empty level
- [ ] Project Gem code builds; a trivial component (for example `HelloComponent` that logs in `Activate`) shows up in the Editor's Add Component menu
- [ ] `.gitignore` covers `build/`, `Cache/`, `user/`; `git status` is clean after a build
- [ ] game/README.md updated with the exact commands that worked

**What to learn**
- How O3DE is organised: engine, project, Gems, the Asset Processor
- CMake presets and the O3DE build configurations (debug, profile, release)
- What a Gem module and a system component are, and where a project Gem registers its components

**Docs**
- Requirements: https://www.o3de.org/docs/welcome-guide/requirements/
- Setup: https://www.o3de.org/docs/welcome-guide/setup/
- Creating projects with the CLI: https://www.o3de.org/docs/welcome-guide/create/creating-projects-using-cli/
- o3de CLI reference: https://www.o3de.org/docs/user-guide/project-config/cli-reference/
- Gems overview: https://www.o3de.org/docs/user-guide/programming/gems/overview/

---

## M1: Movement, top-down camera, chasing enemy

**Goal.** The player moves with WASD, the camera follows from above, one enemy chases the player. All gameplay in C++.

**Acceptance criteria**
- [ ] `PlayerControllerComponent` reads input (WASD or gamepad stick) and moves the player entity
- [ ] Top-down camera follows the player smoothly (fixed angle, configurable height and lag in the Editor)
- [ ] `ChaseComponent` moves an enemy toward the player at a configurable speed
- [ ] Components talk through EBus interfaces declared in `game/Gem/Include/WaveArena/`, no direct pointers between entities
- [ ] All tunables are reflected to the Editor (`EditContext`), no magic numbers in code
- [ ] Reviewed with `/review` and the o3de-expert agent; the user wrote the components

**What to learn**
- Component lifecycle: `Init`, `Activate`, `Deactivate`, `Reflect`
- EBus: request buses vs notification buses, addressing by `EntityId`, connect and disconnect rules
- `TransformBus`, `TickBus` and why tick work should be small
- Input bindings in O3DE

**Docs**
- Components: https://www.o3de.org/docs/user-guide/programming/components/
- Reflection: https://www.o3de.org/docs/user-guide/programming/components/reflection/
- Tick: https://www.o3de.org/docs/user-guide/programming/components/tick/
- EBus: https://www.o3de.org/docs/user-guide/programming/messaging/ebus/
- Input: https://www.o3de.org/docs/user-guide/interactivity/input/

---

## M2: Waves, HP, death, score screen

**Goal.** A full run: waves of enemies spawn, enemies and player have HP, the player dies, a score screen shows the result.

**Acceptance criteria**
- [ ] `HealthComponent` with damage, death notification over EBus, configurable max HP
- [ ] Enemies attack the player in melee range with a cooldown
- [ ] Player can attack (simple projectile or melee arc)
- [ ] `WaveSpawnerComponent` spawns enemy prefabs from a wave config (count, interval, enemy type per wave)
- [ ] Wave config lives in a data file, not in code, so M6 can change it without rebuilding
- [ ] Run summary collected in one struct: score, waves survived, duration, death position, killer type
- [ ] LyShine HUD shows HP, wave and score; a score screen appears on death with a restart button
- [ ] Unit tests (AzTest) for pure logic: damage, wave schedule

**What to learn**
- Spawning prefabs at runtime
- Game loop states (playing, dead, restarting) and who owns them
- LyShine canvases and binding UI to game state
- Testing engine-independent logic in C++

**Docs**
- Entities and prefabs tutorial: https://www.o3de.org/docs/learning-guide/tutorials/entities-and-prefabs/
- UI (LyShine): https://www.o3de.org/docs/user-guide/interactivity/user-interface/
- Testing: https://www.o3de.org/docs/user-guide/testing/

---

## M3: Editor script builds the arena from JSON

**Goal.** A Python script run inside the O3DE Editor reads `tools/editor_scripts/arenas/*.json` and builds the arena: floor, walls, obstacles and spawners.

**Acceptance criteria**
- [ ] JSON format for arenas documented in tools/editor_scripts/README.md, example `arena_01.json`
- [ ] Parsing and validation are pure Python (no `azlmbr` import) and covered by pytest in CI
- [ ] Editor part uses EditorPythonBindings to create entities and set components
- [ ] Running the script twice gives the same level (idempotent: removes what it created before)
- [ ] Invalid JSON fails with a clear message before anything in the level changes

**What to learn**
- O3DE Editor automation and the `azlmbr` API
- Splitting engine-bound code from testable code
- Data-driven level layout

**Docs**
- Editor automation: https://www.o3de.org/docs/user-guide/editor/editor-automation/

---

## M4: CDK stack (API Gateway, Lambda, DynamoDB, S3, budget alert)

**Goal.** A deployed backend: `POST /runs` stores a run, `GET /leaderboard` returns the top 10. Built test-first.

**Acceptance criteria**
- [ ] Domain first: `Run`, `LeaderboardEntry`, validation rules, ports (`RunRepository`, `EventArchive`), with pytest, zero AWS imports
- [ ] DynamoDB adapter and S3 adapter tested with moto
- [ ] Lambda handlers are thin: parse, call domain, map errors to HTTP codes
- [ ] CDK stack: HTTP API, two Lambda functions, one DynamoDB table (on-demand), one S3 bucket (blocked public access, encryption, lifecycle rule)
- [ ] IAM least privilege: each Lambda gets only the actions it uses on the one resource it needs; every permission explained in the PR
- [ ] Throttling on the API stage; request body size limited
- [ ] AWS Budget with an alert at 5 USD
- [ ] `cdk synth` in CI; security-auditor agent run before the first `cdk deploy`
- [ ] import-linter contracts pass

**What to learn**
- Hexagonal architecture in practice
- DynamoDB key design for a leaderboard (partition key, sort key, GSI or not)
- IAM policies, least privilege, CDK grants vs hand-written statements
- Testing AWS code without AWS (moto)

**Docs**
- CDK guide: https://docs.aws.amazon.com/cdk/v2/guide/home.html
- Lambda with Python: https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- HTTP APIs: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html
- DynamoDB design: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-general-nosql-design.html
- S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- IAM best practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- moto: https://docs.getmoto.org/en/latest/
- import-linter: https://import-linter.readthedocs.io/en/stable/
- Hexagonal architecture: https://alistair.cockburn.us/hexagonal-architecture/

---

## M5: Game posts run results and shows top 10

**Goal.** At the end of a run the game sends the run summary to `POST /runs` and the score screen shows the top 10 from `GET /leaderboard`.

**Acceptance criteria**
- [ ] HttpRequestor Gem enabled; requests built in C++ from the M2 run summary
- [ ] API base URL from a config file or the settings registry, not hard-coded
- [ ] Network calls never block the game thread; the UI shows "loading" and "offline" states
- [ ] Failed posts are retried once, then dropped with a log line (no crash, no freeze)
- [ ] Top 10 rendered in LyShine on the score screen
- [ ] Raw run events (including death position) land in S3 for M6

**What to learn**
- Async HTTP in an engine, callbacks back to the main thread
- JSON in C++ (AZ JSON serialization)
- Designing an API contract shared by C++ and Python

**Docs**
- HttpRequestor Gem: https://www.o3de.org/docs/user-guide/gems/reference/network/http-requestor/
- Gems reference: https://www.o3de.org/docs/user-guide/gems/

---

## M6: Death heatmap and wave rebalancing

**Goal.** Use telemetry to make a balance decision and ship it.

**Acceptance criteria**
- [ ] `analytics/` script reads run events from S3 (or a local export) and draws a death heatmap over the arena layout
- [ ] Report with at least: deaths per wave, average run length, top killer types
- [ ] A written conclusion in `docs/learning/M6.md` (what the data says, what to change)
- [ ] A change in the wave config based on it, merged with the report linked in the PR
- [ ] Analytics code tested on a small fixture dataset

**What to learn**
- Turning raw events into a balance decision
- Heatmaps (2D binning) and honest charts
- Closing the loop: data, then config, then new data

**Docs**
- Annotated heatmap example: https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html
- S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html

---

## Out of scope (for now)

- Multiplayer, accounts, authentication beyond a simple player name
- Building the O3DE game in CI (too heavy for free runners); C++ is built and tested locally
- Mobile or console targets
