---
paths:
  - "game/Gem/**"
  - "game/**/*.h"
  - "game/**/*.cpp"
  - "game/**/CMakeLists.txt"
  - "game/**/*.cmake"
---
# C++ and O3DE rules

## Learning mode
The user is learning engine C++. Explain the concept first, point to the O3DE docs, then let the user write the code. Review it like a senior engine programmer: correctness, lifetime, bus connections, performance, readability. Write the code yourself only when the user asks for it.

## O3DE conventions
- Components derive from `AZ::Component`, declare `AZ_COMPONENT(Name, "{UUID}")` with a fresh UUID, and implement `Reflect`, `Activate`, `Deactivate`, `GetProvidedServices`, `GetRequiredServices` where relevant.
- Every component is registered in the Gem module's descriptor list.
- Tunables are reflected with `SerializeContext` and exposed with `EditContext` (sensible defaults, ranges with `Min`/`Max`, tooltips).
- EBus: connect in `Activate`, disconnect in `Deactivate`, always. Request buses for commands, notification buses for events. Address by `AZ::EntityId` where the target is one entity.
- Bus interfaces live in `game/Gem/Include/WaveArena/` (`HealthBus.h`, `WaveBus.h`, ...).
- Use `AZ::TickBus` only when work is needed every frame; keep tick handlers short. Prefer events and timers.
- Use AZStd containers and smart pointers. No raw `new`/`delete`. No exceptions (the engine builds without them).
- Logging with `AZ_Printf`, `AZ_Warning`, `AZ_Error` and a channel name like `"WaveArena"`.
- Never block the main thread (file IO, HTTP). HTTP in M5 goes through the HttpRequestor Gem with callbacks.

## Style
- C++20 as configured by the engine. Follow the engine style: `PascalCase` types and methods, `m_` prefix for members, `s_` for statics, `k` or `Pascal` for constants.
- `#pragma once` in headers. Include what you use. Headers in `Include/` only when other code needs them.
- `const` and `override` everywhere they apply. Pass `AZ::Vector3` and small types by value or const reference consistently.
- Pure logic in classes without entity dependencies, tested with AzTest (GoogleTest) in `game/Gem/Tests/`.
- Format with clang-format (`.clang-format` at repo root) before committing.

## Build
- Configure: `cmake -B game/build/windows -S game -G "Visual Studio 17"`.
- Build: `cmake --build game/build/windows --target WaveArena.GameLauncher Editor --config profile -- /m`.
- Never commit `build/`, `Cache/` or `user/`.
