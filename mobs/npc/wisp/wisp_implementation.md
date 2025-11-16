# Wisp Implementation TODO

## Phase 1 – Data & Registration
- [x] Add `data/mobs/wisp.json` mirroring the skeleton layout but without hostile AI, setting durability 3, speed 64, XP reward 25, drop table (`bone_dust`), and `interaction_event: "wisp_dialogue_event"`.

## Phase 2 – Package Bootstrapping
- [x] Create package exports in `systems/mobs/npc/wisp/__init__.py` for the animation, behaviours, dialogue rules, models, and JSON helpers.
- [x] Implement a lightweight `wisp_spec_loader.py` that wraps the core species loader, preserving custom fields like `interaction_event`.

## Phase 3 – Animation & View
- [x] Implement a wisp animation helper that loads `assets/mobs/wisp/wisp.png` as a 9×7 sheet (173×197 per sprite), skips the final three blanks, and returns the 60-frame loop with a configurable frame duration (default 0.2 s).

## Phase 4 – Behaviours & AI
- [x] Implement `behaviors.py` handling:
  - Void damage identical to skeletons.
  - Standard combat/push interactions so the player can damage or shove the wisp.
  - Hourly wander triggered by `GAME_HOUR_PASSED`, moving one tile in a random valid direction without entering void or invalid tiles.

## Phase 5 – Dialogue & Interaction Event
- [x] Implement `dialogue_rules.py` to register the `wisp_dialogue_event`, opening the `wisp_dialogue` JSON via the interactibles pipeline.
- [x] Extend `shrine_event` to spawn the wisp at the portal tile when the dialogue requests `spawn_wisp`, ensuring the NPC persists thereafter.

## Phase 6 – Integration Touchpoints
- [ ] Wire the mob manager or relevant bootstrap to recognise the wisp species, using the new reader/behaviour modules.
- [ ] Document assumptions (spawn location provided by shrine event, wander radius, persistence) in package docstrings or comments as needed.
