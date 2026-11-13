---
name: o3de-component
description: Use when the user wants to add a new O3DE component or EBus to the WaveArena Gem, or asks why a component does not show up in the Editor. Gives a checklist and teaching notes; the user writes the code.
---
# Adding a component to the WaveArena Gem

Learning mode: walk the user through these steps, explain each, let them write the code, then review.

## Checklist
1. **Header and source** in `game/Gem/Source/<Name>Component.h/.cpp` (follow the template layout found in M0).
2. **Class**: derives from `AZ::Component` (plus bus handlers it implements). `AZ_COMPONENT(<Name>Component, "{NEW-UUID}")`. Generate a fresh UUID, never copy one.
3. **Reflect**: `SerializeContext` with a `Version(1)` and every field; `EditContext` with category `"WaveArena"`, `AppearsInAddComponentMenu` for `"Game"`, ranges and tooltips for tunables.
4. **Services**: `GetProvidedServices`, `GetRequiredServices` (for example requires `TransformService`).
5. **Lifecycle**: connect buses in `Activate`, disconnect in `Deactivate`. Nothing heavy in the constructor.
6. **Bus** (if other components talk to it): interface in `game/Gem/Include/WaveArena/<Name>Bus.h` with `EBusTraits` (address policy `ById` with `AZ::EntityId` for per-entity buses), plus a notification bus for events.
7. **Register** the descriptor in the Gem module (`m_descriptors.insert(...)`).
8. **CMake**: add the files to the Gem's `.cmake` file list.
9. **Build** profile, open the Editor, add the component to an entity, check the reflected fields.
10. **Test** pure logic with AzTest in `game/Gem/Tests/`.

## Common reasons a component does not show up
- Not registered in the module descriptors.
- Missing `AppearsInAddComponentMenu` or wrong menu name.
- File not listed in the `.cmake` file list, so it was never compiled.
- Editor running an old build: rebuild the `Editor` target, not only the launcher.

## Docs
- Components: https://www.o3de.org/docs/user-guide/programming/components/
- Reflection: https://www.o3de.org/docs/user-guide/programming/components/reflection/
- EBus: https://www.o3de.org/docs/user-guide/programming/messaging/ebus/
