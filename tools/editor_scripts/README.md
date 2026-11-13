# tools/editor_scripts/ (M3)

Python run inside the O3DE Editor to build the arena from a JSON file.

Split:
- `arena_model.py` (to write in M3): load and validate JSON into dataclasses. Pure Python, tested by pytest in CI.
- `build_arena.py` (to write in M3): the only module importing `azlmbr`. Creates entities from the validated model.

Run in the Editor: Tools, Python Scripts, or from the Editor console: `pyRunFile <path>/build_arena.py arenas/arena_01.json`.

## Arena JSON (draft, finalise in M3)

Units are meters, origin at the arena center, Z up.

| Field | Type | Meaning |
|---|---|---|
| `version` | int | Format version, currently 1 |
| `name` | string | Arena name |
| `size` | [x, y] | Floor size |
| `walls` | list | `{ "from": [x, y], "to": [x, y], "height": h }` |
| `obstacles` | list | `{ "prefab": name, "position": [x, y], "rotation_deg": r }` |
| `spawners` | list | `{ "id": name, "position": [x, y] }` used by `WaveSpawnerComponent` |
| `player_start` | [x, y] | Player spawn point |

Example: [arenas/arena_01.json](arenas/arena_01.json).
