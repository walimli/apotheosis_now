"""Moss generation utilities for world_builder.

Per-island process:
- 50% chance the island has moss
- Seed 1 random moss tile within that island
- Run N steps of 8-neighbor cellular automata (N in [1, 10])
  - Survive: moss survives with >=3 moss neighbors
  - Birth: non-moss land becomes moss with >=4 moss neighbors
- Convert moss cells to tile code 4; other land stays as-is

All randomness is deterministic per chunk and island using the provided seed.
"""
from __future__ import annotations

from typing import Generator, Iterable, List, Sequence, Tuple

import numpy as np

TileArray = np.ndarray
Coord = Tuple[int, int]


def apply_moss(
    grid: TileArray,
    chunk_x: int,
    chunk_y: int,
    seed: int,
    *,
    island_moss_probability: float = 0.5,
    birth_probability: float = 0.65,
    min_steps: int = 2,
    max_steps: int = 6,
    max_coverage: float = 0.30,
) -> TileArray:
    """Return a copy of grid with moss (code 4) applied per island.

    Expects grid to already contain per-island biome codes (1/2/3) for land.
    """
    if grid.ndim != 2:
        raise ValueError("grid must be two-dimensional")
    if not (0.0 <= island_moss_probability <= 1.0):
        raise ValueError("island_moss_probability must be within [0, 1]")
    if not (0.0 <= birth_probability <= 1.0):
        raise ValueError("birth_probability must be within [0, 1]")
    if min_steps < 1 or max_steps < min_steps:
        raise ValueError("invalid moss CA step bounds")
    if not (0.0 < max_coverage <= 1.0):
        raise ValueError("max_coverage must be within (0, 1]")

    rows, cols = grid.shape
    result = grid.astype(np.int8, copy=True)

    land_mask = result != 0
    islands = _find_islands(land_mask)

    base_rng = _rng_for_chunk(seed, chunk_x, chunk_y)

    for idx, island in enumerate(islands):
        # Deterministic per-island rng by mixing base seed with island index
        rng = _rng_for_island(base_rng, idx)
        if island_moss_probability < 1.0 and float(rng.random()) >= island_moss_probability:
            continue
        if not island:
            continue
        steps = int(rng.integers(min_steps, max_steps + 1))
        seed_idx = int(rng.integers(0, len(island)))
        moss = np.zeros((rows, cols), dtype=bool)
        island_mask_local = np.zeros((rows, cols), dtype=bool)
        for r, c in island:
            island_mask_local[r, c] = True
        sr, sc = island[seed_idx]
        moss[sr, sc] = True
        island_area = int(island_mask_local.sum())
        for _ in range(steps):
            neighbor_count = _neighbor_count_8(moss)
            # Option A rules: growth from a single seed with probabilistic births
            survive = moss & (neighbor_count >= 1)
            eligible_birth = (~moss) & island_mask_local & (neighbor_count >= 1)
            if eligible_birth.any():
                rand_vals = np.zeros((rows, cols), dtype=np.float64)
                rand_vals[eligible_birth] = rng.random(int(eligible_birth.sum()))
                birth = eligible_birth & (rand_vals < float(birth_probability))
            else:
                birth = eligible_birth
            moss = survive | birth
            # Early stop based on coverage
            moss_count = int(moss.sum())
            if island_area > 0 and (moss_count / island_area) >= max_coverage:
                break
        # Safety net: ensure at least the original seed remains moss
        if not moss.any():
            moss[sr, sc] = True
        # Encode moss as overlay: base*10 + 4 (14/24/34)
        result[moss] = (result[moss] * 10 + 4).astype(result.dtype)

    return result


def _find_islands(land_mask: TileArray) -> List[List[Coord]]:
    rows, cols = land_mask.shape
    visited = np.zeros_like(land_mask, dtype=bool)
    islands: List[List[Coord]] = []

    for r in range(rows):
        for c in range(cols):
            if not land_mask[r, c] or visited[r, c]:
                continue
            stack = [(r, c)]
            visited[r, c] = True
            component: List[Coord] = []
            while stack:
                cr, cc = stack.pop()
                component.append((cr, cc))
                # 4-connected neighbors keep island boundaries tight
                if cr > 0 and land_mask[cr - 1, cc] and not visited[cr - 1, cc]:
                    visited[cr - 1, cc] = True
                    stack.append((cr - 1, cc))
                if cr + 1 < rows and land_mask[cr + 1, cc] and not visited[cr + 1, cc]:
                    visited[cr + 1, cc] = True
                    stack.append((cr + 1, cc))
                if cc > 0 and land_mask[cr, cc - 1] and not visited[cr, cc - 1]:
                    visited[cr, cc - 1] = True
                    stack.append((cr, cc - 1))
                if cc + 1 < cols and land_mask[cr, cc + 1] and not visited[cr, cc + 1]:
                    visited[cr, cc + 1] = True
                    stack.append((cr, cc + 1))
            islands.append(component)
    return islands


def _neighbor_count_8(mask: TileArray) -> TileArray:
    # 8-neighbor count via summed shifted masks
    padded = np.pad(mask.astype(np.int8), 1, mode="constant", constant_values=0)
    return (
        padded[:-2, :-2]
        + padded[:-2, 1:-1]
        + padded[:-2, 2:]
        + padded[1:-1, :-2]
        + padded[1:-1, 2:]
        + padded[2:, :-2]
        + padded[2:, 1:-1]
        + padded[2:, 2:]
    )


def _rng_for_chunk(seed: int, chunk_x: int, chunk_y: int) -> np.random.Generator:
    mask = (1 << 64) - 1
    mul_a = 6364136223846793005
    mul_b = 1442695040888963407
    mul_c = 22695477
    mix = (int(seed) * mul_a) & mask
    mix ^= (int(chunk_x) * mul_b) & mask
    mix ^= (int(chunk_y) * mul_c) & mask
    return np.random.default_rng(np.uint64(mix))


def _rng_for_island(base_rng: np.random.Generator, index: int) -> np.random.Generator:
    # Derive a new generator from base by mixing in index via a jump in sequence
    # Use base rng to produce a seed deterministically per index
    # (sequence is deterministic given base seed)
    _ = base_rng.random(index + 1)
    seed_val = int(base_rng.integers(0, 2**63))
    return np.random.default_rng(np.uint64(seed_val))
