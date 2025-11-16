"""Lightweight tile helpers reused by the legacy pathfinding stack."""

from __future__ import annotations

import math
from typing import Optional, Tuple

from constants import CHUNK_SIZE_TILES, TILE_SIZE

TileCoord = Tuple[int, int]


def world_to_tile(world_value: float, tile_size: int = TILE_SIZE) -> int:
    return int(math.floor(world_value / tile_size))


def tile_to_world_center(tile_x: int, tile_y: int, tile_size: int = TILE_SIZE) -> Tuple[float, float]:
    half = tile_size * 0.5
    return (tile_x * tile_size + half, tile_y * tile_size + half)


def get_tile_id(world, tile_x: int, tile_y: int, *, chunk_size: Optional[int] = None) -> Optional[int]:
    chunks = getattr(world, "chunks", None)
    if chunks is None:
        raise AttributeError("world must expose a 'chunks' mapping for pathfinding")
    if chunk_size is None:
        chunk_size = int(getattr(world, "chunk_size", CHUNK_SIZE_TILES))
    chunk_x = tile_x // chunk_size
    chunk_y = tile_y // chunk_size
    chunk = chunks.get((chunk_x, chunk_y))
    if chunk is None:
        return None
    local_x = tile_x - chunk_x * chunk_size
    local_y = tile_y - chunk_y * chunk_size
    if not (0 <= local_x < chunk_size and 0 <= local_y < chunk_size):
        return None
    return int(chunk[int(local_y), int(local_x)])


def is_walkable_tile(tile_id: Optional[int]) -> bool:
    if tile_id is None:
        return False
    return tile_id != 0

