"""Grid helpers for tile-aligned fence placement."""

from __future__ import annotations
from typing import Tuple

from constants import TILE_SIZE

TileCoord = Tuple[int, int]
Vec2f = Tuple[float, float]


def world_to_tile(world_pos: Vec2f) -> TileCoord:
    """Convert a world-space position to tile coordinates."""
    x, y = world_pos
    return (int(x // TILE_SIZE), int(y // TILE_SIZE))


def tile_to_world_center(tile: TileCoord) -> Vec2f:
    """Return the world-space center for the given tile coordinate."""
    tx, ty = tile
    center_x = (tx + 0.5) * TILE_SIZE
    center_y = (ty + 0.5) * TILE_SIZE
    return (center_x, center_y)


def snap_world_to_tile_center(world_pos: Vec2f) -> Vec2f:
    """Snap an arbitrary world position to the center of its tile."""
    return tile_to_world_center(world_to_tile(world_pos))
