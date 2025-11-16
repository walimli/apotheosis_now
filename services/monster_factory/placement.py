"""Tile selection helpers for monster spawning."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

import numpy as np

from constants import TILE_CODE_MOSS_OVERLAY, TILE_CODE_VOID

TileCoord = Tuple[int, int]


def find_regions(mask: np.ndarray) -> List[List[TileCoord]]:
    rows, cols = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    regions: List[List[TileCoord]] = []
    for row in range(rows):
        for col in range(cols):
            if not mask[row, col] or visited[row, col]:
                continue
            stack = [(row, col)]
            visited[row, col] = True
            region: List[TileCoord] = []
            while stack:
                r, c = stack.pop()
                region.append((c, r))
                if r > 0 and mask[r - 1, c] and not visited[r - 1, c]:
                    visited[r - 1, c] = True
                    stack.append((r - 1, c))
                if r + 1 < rows and mask[r + 1, c] and not visited[r + 1, c]:
                    visited[r + 1, c] = True
                    stack.append((r + 1, c))
                if c > 0 and mask[r, c - 1] and not visited[r, c - 1]:
                    visited[r, c - 1] = True
                    stack.append((r, c - 1))
                if c + 1 < cols and mask[r, c + 1] and not visited[r, c + 1]:
                    visited[r, c + 1] = True
                    stack.append((r, c + 1))
            regions.append(region)
    return regions


def eligible_coordinates(
    tiles: np.ndarray,
    eligible_tiles: Optional[frozenset[int]],
) -> List[TileCoord]:
    coords: List[TileCoord] = []
    rows, cols = tiles.shape
    for row in range(rows):
        for col in range(cols):
            coord = (col, row)
            if tile_is_eligible(tiles, coord, eligible_tiles):
                coords.append(coord)
    return coords


def tile_is_eligible(
    tiles: np.ndarray,
    coord: TileCoord,
    eligible_tiles: Optional[frozenset[int]],
    *,
    include_void: bool = False,
) -> bool:
    tile_value = int(tiles[coord[1], coord[0]])
    normalized = normalize_tile_value(tile_value)
    if tile_value == TILE_CODE_VOID and not include_void:
        return False
    if eligible_tiles is None:
        return tile_value != TILE_CODE_VOID
    return tile_value in eligible_tiles or normalized in eligible_tiles


def normalize_tile_value(tile_value: int) -> int:
    if tile_value >= 10 and (tile_value % 10) == TILE_CODE_MOSS_OVERLAY:
        return tile_value // 10
    return tile_value


def choose_positions(
    available: Sequence[TileCoord],
    count: int,
    allow_shared: bool,
    rng: random.Random,
) -> List[TileCoord]:
    if not available or count <= 0:
        return []
    if allow_shared:
        return [available[rng.randrange(len(available))] for _ in range(count)]
    unique = list(available)
    rng.shuffle(unique)
    return list(unique[: min(count, len(unique))])


def filter_by_player_range(
    coords: Sequence[TileCoord],
    chunk_key: Tuple[int, int],
    chunk_size: int,
    player_tile: Optional[TileCoord],
    player_range: Optional[Tuple[float, float]],
) -> List[TileCoord]:
    if not coords:
        return []
    if player_tile is None or player_range is None:
        return list(coords)
    min_dist, max_dist = player_range
    filtered: List[TileCoord] = []
    chunk_base_x = chunk_key[0] * chunk_size
    chunk_base_y = chunk_key[1] * chunk_size
    for coord in coords:
        world_tx = chunk_base_x + coord[0]
        world_ty = chunk_base_y + coord[1]
        dx = float(world_tx - player_tile[0])
        dy = float(world_ty - player_tile[1])
        dist = math.hypot(dx, dy)
        if dist < min_dist:
            continue
        if max_dist != float("inf") and dist > max_dist:
            continue
        filtered.append(coord)
    return filtered


__all__ = [
    "TileCoord",
    "find_regions",
    "eligible_coordinates",
    "tile_is_eligible",
    "normalize_tile_value",
    "choose_positions",
    "filter_by_player_range",
]
