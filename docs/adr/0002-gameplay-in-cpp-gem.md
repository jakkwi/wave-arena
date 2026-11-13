# 0002: Gameplay in a C++ project Gem, tools in Python

**Status:** Accepted

## Context
O3DE supports gameplay in C++, Lua and Script Canvas. The goal of this project is to learn engine C++ (components, EBus, reflection).

## Decision
- All gameplay (player, enemies, health, waves, run summary, HTTP) is C++ in the project Gem under `game/Gem/`.
- Components communicate only through EBus interfaces in `game/Gem/Include/WaveArena/`.
- Tunables are reflected to the Editor; wave definitions are data files so balance changes need no rebuild.
- Editor tooling (arena generation) is Python with EditorPythonBindings.

## Consequences
- Slower iteration than Script Canvas, more to learn. That is the point.
- C++ is built and tested locally only; CI does not build the engine.
