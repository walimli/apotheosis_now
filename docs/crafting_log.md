# Crafting Package Catalog

## Phase 1 - Data & Assets Survey
- `services/crafting/crafting_assets.py` loads UI art exclusively from disk via `assets/ui/buttons/crafting_button` and `assets/ui/crafting_atlas/atlas_{1-4}` plus `crafting_success` / `crafting_failure`. It depends on `systems.asset_loader.notification_assets.ButtonImages`, so the notification asset loader must already be initialized before crafting assets are requested.
- Atlas animation state comes from four loop folders and two result sequences. Missing PNGs raise `FileNotFoundError`, so asset folders must exist in the project.
- Ingredient storage (`CraftingAtlas`) supports three unique stacks by default and only interacts with an `inventory` via its `add()` method when refunding or clearing. As long as inventory item IDs stay consistent with crafting data, no other coupling exists.
- Recipe data lives in `data/formulas/crafting_recipes.json` and is loaded by `CraftingRecipes`. Each entry expects `{ id, inputs: [{ item, qty }], output: { item, qty }, success_rate, health_cost, soul_cost }`. IDs are opaque strings; loader validation previously only checked structural correctness.
- `CraftingRecipes` relies on `SoulCosts.CRAFTING_DEFAULT` to provide default soul drain values. There are no fallbacks for malformed data: errors abort load.

## Phase 2 - Core Logic Review
- `CraftOutcome` captures each crafting attempt with `status`, `recipe_id`, `output_item`, `produced`, `lost_output`, etc., and provides helpers for quick success/failure checks.
- `CraftingEngine` composes the atlas state, recipes, and assets. The owning system must assign `engine.cursor` to the inventory cursor; the engine does not instantiate input helpers on its own.
- `attempt_craft()` enforces a strict pipeline: block when animations play or the cursor carries items, take an ordered atlas snapshot, match a recipe, roll success chances, validate soul cost, clear the atlas, deposit results via `Inventory.add()`, and apply health/soul costs. Failures trigger the failure animation and record their reason.
- `_result_lock` prevents spamming the atlas while animations run; callbacks release the lock. Overflow output is dropped (but reported) if inventory rejects it.
- `crafting_recipes.py` exposes `CraftingRecipe` with `matches_ordered` and `max_crafts`. Matching is order-sensitive and requires exact ingredient type alignment.

## Phase 3 - UI & System Integration
- `CraftingButton` subclasses `systems.notifications.ui.button.ImageButton` to provide a persistent HUD toggle anchored to the bottom-right corner.
- `CraftingSystem` glues inventory, health, and soul services to the crafting engine. It expects an inventory cursor API (`carrying`, `start_drag`, etc.) and relies on those services for transactions.
- Opening returns focus to crafting, closing refunds atlas contents to inventory and clears the cursor. A listener hook broadcasts active state changes.
- Input handling currently listens to raw `pygame` mouse events (`MOUSEMOTION`, `MOUSEBUTTONDOWN`) and delegates to helper methods for atlas/ingredient interactions. Hover state caches cursor position instead of polling per frame.
- Rendering is split so HUD code draws the toggle button at screen scale (`draw_button`) while the base surface draws atlas animations and ingredient slots (`draw_ui`). Icons for slots come from `systems.player.components.inventory_package.items.get_icon`, so inventory data must stay synced with icon assets.

## Phase 4 - Dependency & Gap Analysis
- External dependencies:
  - `systems.notifications.ui.button.ImageButton` and related notification UI infrastructure.
  - `systems.asset_loader.notification_assets.ButtonImages` for button state imagery.
  - Player subsystems: `Inventory` (with cursor support), `Health`, `Soul`, and icon lookups via `get_icon`.
  - An input/cursor service capable of routing events to `CraftingSystem` helpers; native integration with the ECS input bus is still pending.
- Key gaps prior to implementation:
  1. **Inventory ID alignment** - Recipes referenced legacy IDs; we must ensure all inputs/outputs exist in `data/inventory/coins.json` or `data/inventory/medallions.json`.
  2. **Service duplication** - Crafting duplicates some cursor logic; long term it should delegate to centralized cursor/input services.
  3. **Event wiring** - Mouse handling is direct pygame polling; integrating with the Play Input Bus requires an event bridge.
  4. **Asset availability** - Missing atlas/button art will crash the loader; verify assets shipped with the current project.
  5. **Atlas capacity** - `CraftingAtlas` allows only three unique stacks; expanding recipe complexity may require revisiting this limit.

## Phase A - Data Alignment & Validation (Implementation)
- Updated crafting recipes so outputs (e.g., health and soul pills) reference the medallion inventory IDs, keeping all recipe items within the new split inventory catalogs.
- Added inventory-backed validation in `services/crafting/crafting_recipes.py` that loads the merged item registry and raises a `ValueError` if any ingredient or output ID is unknown, preventing silent mismatches when recipes change.
- Phase A close-out: the data layer now fails fast on bad IDs, so we can proceed to service bootstrapping knowing recipes match the active inventory definitions.

## Phase B - Service Bootstrapping (Implementation)
- Replaced all lingering `systems.*` imports in the crafting package so it now depends on the actual ECS-era modules: `services.asset_loader`, `services.notifications`, `services.inventory`, and `ecs_core.components`.
- Extended the ECS `Health` and `Soul` components with minimal imperative helpers (`take_damage`, `heal`, `can_spend`, `consume`, `announce_blocked`) so legacy-style services like crafting (and future landscaping hooks) can manipulate the player stats without inventing duplicate wrappers.
- `PlayState` now owns a `CraftingSystem` that's tied directly to the player inventory/health/soul components, repositions itself with the display, and receives update ticks alongside the other services.
- Wired the existing `CraftingInputAdapter` into the play input bus/context so cursor moves, button presses, and crafting toggles flow through the shared `PlayInputContext`. The adapter keeps the HUD button hover state in sync and routes primary/secondary actions to the crafting atlas, paving the way for HUD rendering in the next phase.

## Phase C - UI Integration (Implementation)
- `PlayState.render()` now calls `CraftingSystem.draw_ui(surface)` so the atlas animation and ingredient slots appear on the base play surface whenever crafting is active.
- `PlayState.render_hud()` calls `CraftingSystem.draw_button(screen)` after the HUD manager renders, ensuring the bottom-right toggle button displays at screen scale.
- `CraftingSystem.reposition()` now accepts separate base-surface and screen dimensions; PlayState feeds it the logical base size (for atlas placement) and the actual screen size (for the HUD button). This keeps the atlas centered even when the display is scaled/letterboxed while preserving button alignment on the HUD.
- The `CraftingInputAdapter` maps screen-space cursor coordinates into the base surface on demand (while still passing raw screen coords to the toggle button), so ingredient interactions line up with the atlas even though the window is rendered at 2x scale. This keeps other systems (e.g., landscaping) untouched while giving crafting the base-space positions it needs.
