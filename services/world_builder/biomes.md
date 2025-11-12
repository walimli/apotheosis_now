Biomes and Moss Plan

Objectives
- Introduce multiple land biomes without changing the void:land ratio.
- Ensure each island is homogeneous to a single biome, except for moss mixing.
- Generate moss per island using a seeded cellular automata (CA) spread.
- Update harvesting and placement to use biome-specific coins.
- Render moss as an overlay with soft-corner edges using the moss tilesheet.

Tile Codes (final)
- 0 = void
- 1 = clay
- 2 = redrock
- 3 = stone
- 14 = moss over clay (overlay)
- 24 = moss over redrock (overlay)
- 34 = moss over stone (overlay)

Encoding Summary
- Moss overlay code = base*10 + 4 (no bare 4 tiles are used).

Island Biomes
- Detect islands as connected components over the binary land mask.
- Assign one biome per island using weighted probabilities:
  - clay: 50%
  - stone: 30%
  - redrock: 20%
- After current generation (0/1), rewrite each island's land cells to the assigned biome code (1/2/3).

Moss Generation (Option A)
- Per-island 50% chance to enable moss.
- If enabled, pick one random land tile on that island as the initial moss seed.
- Choose N steps within [2, 6] per island (deterministic per island).
- CA rule (8-neighbor, island land only):
  - Survive: a moss cell survives if it has at least 1 moss neighbor.
  - Birth: a non-moss land cell becomes moss if it has at least 1 moss neighbor and random < birth_probability (0.65 default).
- Early stop when moss coverage reaches max_coverage = 30% of the island.
- Moss is allowed on all land tiles of the island (edges included).
- Convert moss cells to overlay codes by encoding base as base*10+4 (14/24/34); non-moss land remains 1/2/3.

WorldBuilder Changes
- Keep existing cellular steps, pruning, and padding.
- Post-process the binary land grid:
  1) Find islands.
  2) Assign a weighted biome id to each island.
  3) Rewrite land cells to that biome id (1/2/3).
  4) For islands with moss, run the CA and encode moss overlays as 14/24/34 (base*10+4).

Renderer Integration
- Decode overlay at render time:
  - base = (v // 10) if v >= 10 else v (0/1/2/3)
  - moss_mask = (v >= 10)
- Render base land (1/2/3) using biome tilesheets under assets/tiles/biomes/ (clay/red/stone).
- Render moss overlay as a second pass using the moss tilesheet (code 4), with the same orientation and soft-corner selection as base land to avoid square boundaries.
- Classification treats any non-zero as land; overlays remain land for gameplay systems.

Inventory and Harvesting
- Harvest rewards:
  - Non-moss land (1/2/3): 1x biome coin (1→clay_coin, 2→redrock_coin, 3→stone_coin).
  - Moss overlay (14/24/34): 1x spore_coin + 1x biome coin for the base (decode base as v//10).
- Placement:
  - Placing clay_coin/redrock_coin/stone_coin on void sets tile to 1/2/3 respectively.

Dependent Systems
- Systems that check tile codes should decode base for overlays (v>=10 → v//10), or rely on classification where possible.
- Farming growth previously targeted (1, 2); update logic to include (1, 2, 3) and optionally treat overlays (14/24/34) as land-equivalent.
- Player spawn utilities already treat non-zero as land; no changes required.

