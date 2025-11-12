"""Camera utilities for chunk visibility calculations."""
from __future__ import annotations

import math
from typing import List, Tuple


def compute_visible_chunks(
    camera_x: int,
    camera_y: int,
    screen_width: int,
    screen_height: int,
    *,
    chunk_size: int = 32,
    tile_size: int = 64,
) -> List[Tuple[int, int]]:
    """Return chunk coordinates that intersect the camera view plus one-chunk padding."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if tile_size <= 0:
        raise ValueError("tile_size must be a positive integer")
    if screen_width <= 0 or screen_height <= 0:
        return []

    chunk_pixels = chunk_size * tile_size
    pad = chunk_pixels

    min_world_x = camera_x - pad
    min_world_y = camera_y - pad
    max_world_x = camera_x + screen_width + pad - 1
    max_world_y = camera_y + screen_height + pad - 1

    min_chunk_x = _world_to_chunk(min_world_x, chunk_pixels)
    max_chunk_x = _world_to_chunk(max_world_x, chunk_pixels)
    min_chunk_y = _world_to_chunk(min_world_y, chunk_pixels)
    max_chunk_y = _world_to_chunk(max_world_y, chunk_pixels)

    visible: List[Tuple[int, int]] = []
    for chunk_y in range(min_chunk_y, max_chunk_y + 1):
        for chunk_x in range(min_chunk_x, max_chunk_x + 1):
            visible.append((chunk_x, chunk_y))
    return visible


def _world_to_chunk(world_coord: int, chunk_pixels: int) -> int:
    return math.floor(world_coord / chunk_pixels)
