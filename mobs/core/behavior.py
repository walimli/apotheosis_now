from __future__ import annotations

import math
from typing import Callable, Iterable, Optional, Sequence, Tuple

from constants import CHUNK_SIZE_TILES, TILE_SIZE

Vector = Tuple[float, float]
Point = Tuple[float, float]
TileCoord = Tuple[int, int]

def _resolve_protection_checker(world) -> Callable[[TileCoord], bool]:
    """Resolve protection check from the placeables system, not PlayState."""
    placeables = getattr(world, "placeables", None)
    protection = getattr(placeables, "protection", None) if placeables is not None else None
    checker = getattr(protection, "is_tile_protected", None) if protection is not None else None
    if not callable(checker):
        raise AttributeError(
            "World.placeables.protection must expose is_tile_protected(tile_coord) for mob behavior"
        )

    def _wrapped(tile: TileCoord) -> bool:
        if not isinstance(tile, tuple) or len(tile) != 2:
            raise ValueError("tile_coord must be a tuple[2]")
        tx, ty = int(tile[0]), int(tile[1])
        return bool(checker((tx, ty)))

    return _wrapped


def _resolve_sizes(world) -> Tuple[int, int]:
    tile_size = int(getattr(world, "tile_size", TILE_SIZE))
    chunk_size = int(getattr(world, "chunk_size", CHUNK_SIZE_TILES))
    return tile_size, chunk_size


def world_to_tile(world_value: float, tile_size: int) -> int:
    return int(math.floor(world_value / tile_size))


def tile_to_world_center(tile_x: int, tile_y: int, tile_size: int) -> Point:
    half = tile_size * 0.5
    return (tile_x * tile_size + half, tile_y * tile_size + half)


def get_tile_id(
    world,
    tile_x: int,
    tile_y: int,
    *,
    chunk_size: Optional[int] = None,
) -> Optional[int]:
    chunks = getattr(world, "chunks", None)
    if chunks is None:
        raise AttributeError("World instance must expose a 'chunks' mapping")

    if chunk_size is None:
        _, chunk_size = _resolve_sizes(world)

    chunk_x = tile_x // chunk_size
    chunk_y = tile_y // chunk_size
    chunk = chunks.get((chunk_x, chunk_y))
    if chunk is None:
        return None

    local_x = tile_x - chunk_x * chunk_size
    local_y = tile_y - chunk_y * chunk_size
    if not (0 <= local_x < chunk_size and 0 <= local_y < chunk_size):
        return None

    value = chunk[int(local_y), int(local_x)]
    return int(value)


def get_tile_id_at_world(
    world,
    world_x: float,
    world_y: float,
    *,
    tile_size: Optional[int] = None,
    chunk_size: Optional[int] = None,
) -> Optional[int]:
    if tile_size is None or chunk_size is None:
        resolved_tile_size, resolved_chunk_size = _resolve_sizes(world)
        if tile_size is None:
            tile_size = resolved_tile_size
        if chunk_size is None:
            chunk_size = resolved_chunk_size

    tile_x = world_to_tile(world_x, tile_size)
    tile_y = world_to_tile(world_y, tile_size)
    return get_tile_id(world, tile_x, tile_y, chunk_size=chunk_size)


def is_walkable_tile(tile_id: Optional[int]) -> bool:
    if tile_id is None:
        return False
    return tile_id != 0


def entity_center(top_left: Point, width: float, height: float) -> Point:
    return (top_left[0] + width * 0.5, top_left[1] + height * 0.5)


def _footprint_points(top_left: Point, width: float, height: float) -> Iterable[Point]:
    x, y = top_left
    inset = 1.0
    max_x = x + max(width - inset, inset)
    max_y = y + max(height - inset, inset)
    return (
        (x + inset, y + inset),
        (max_x, y + inset),
        (x + inset, max_y),
        (max_x, max_y),
        (x + width * 0.5, y + height * 0.5),
    )


def can_spawn_at(
    world,
    top_left: Point,
    *,
    width: float = TILE_SIZE,
    height: float = TILE_SIZE,
) -> bool:
    tile_size, chunk_size = _resolve_sizes(world)
    protection = _resolve_protection_checker(world)
    for px, py in _footprint_points(top_left, width, height):
        tile_x = world_to_tile(px, tile_size)
        tile_y = world_to_tile(py, tile_size)
        tile_id = get_tile_id(
            world, tile_x, tile_y, chunk_size=chunk_size
        )
        if not is_walkable_tile(tile_id):
            return False
        if protection((tile_x, tile_y)):
            return False

    return True


def normalize(vec: Vector) -> Vector:
    vx, vy = vec
    length = math.hypot(vx, vy)
    if length <= 1e-6:
        return (0.0, 0.0)
    return (vx / length, vy / length)