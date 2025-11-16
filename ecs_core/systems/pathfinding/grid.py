from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence, Set, Tuple

from constants import CHUNK_SIZE_TILES, TILE_SIZE
from ecs_core.systems.pathfinding import behavior

Point = Tuple[float, float]
Size = Tuple[float, float]
TileCoord = Tuple[int, int]


def _resolve_protection_checker(world) -> Callable[[TileCoord], bool]:
    """Resolve protection check from world.placeables.protection."""
    placeables = getattr(world, "placeables", None)
    protection = (
        getattr(placeables, "protection", None) if placeables is not None else None
    )
    checker = (
        getattr(protection, "is_tile_protected", None)
        if protection is not None
        else None
    )
    if not callable(checker):
        return lambda _tile: False

    def _wrapped(tile: TileCoord) -> bool:
        if not isinstance(tile, tuple) or len(tile) != 2:
            raise ValueError("tile_coord must be a tuple[2]")
        tx, ty = int(tile[0]), int(tile[1])
        return bool(checker((tx, ty)))

    return _wrapped


@dataclass(frozen=True)
class AggressiveGridContext:
    """Lightweight view of the world grid for aggressive mob pathfinding."""

    world: object
    tile_size: int
    chunk_size: int
    _protection: Callable[[TileCoord], bool]

    @classmethod
    def from_world(
        cls,
        world,
        *,
        walkable_tiles: Optional[Sequence[int]] = None,
    ) -> "AggressiveGridContext":
        if world is None:
            raise ValueError("AggressiveGridContext requires a world instance")

        tile_size = int(getattr(world, "tile_size", TILE_SIZE))
        chunk_size = int(getattr(world, "chunk_size", CHUNK_SIZE_TILES))

        protection = _resolve_protection_checker(world)

        return cls(
            world=world,
            tile_size=tile_size,
            chunk_size=chunk_size,
            _protection=protection,
        )

    def world_to_tile(self, world_x: float, world_y: float) -> TileCoord:
        tx = behavior.world_to_tile(world_x, self.tile_size)
        ty = behavior.world_to_tile(world_y, self.tile_size)
        return tx, ty

    def tile_to_world_center(self, tile: TileCoord) -> Point:
        return behavior.tile_to_world_center(tile[0], tile[1], self.tile_size)

    def get_tile_id(self, tile: TileCoord) -> Optional[int]:
        return behavior.get_tile_id(
            self.world, tile[0], tile[1], chunk_size=self.chunk_size
        )

    def is_walkable(self, tile: TileCoord) -> bool:
        tile_id = self.get_tile_id(tile)
        if not behavior.is_walkable_tile(tile_id):
            return False
        return not bool(self._protection((int(tile[0]), int(tile[1]))))

    def is_world_position_walkable(self, world_x: float, world_y: float) -> bool:
        tile = self.world_to_tile(world_x, world_y)
        return self.is_walkable(tile)


def collect_blocking_tiles(
    context: AggressiveGridContext,
    blockers: Iterable[Tuple[Point, Size]],
) -> Set[TileCoord]:
    """Convert blocking bounding boxes into a set of tile coordinates."""
    tiles: Set[TileCoord] = set()
    for idx, (origin, footprint) in enumerate(blockers):
        if origin is None or footprint is None:
            raise ValueError(f"Blocker #{idx} is missing origin or footprint")
        ox, oy = float(origin[0]), float(origin[1])
        width, height = float(footprint[0]), float(footprint[1])
        if width <= 0.0 or height <= 0.0:
            raise ValueError(f"Blocker #{idx} footprint must be positive")

        min_tile_x = behavior.world_to_tile(ox, context.tile_size)
        min_tile_y = behavior.world_to_tile(oy, context.tile_size)
        max_tile_x = behavior.world_to_tile(ox + width - 1e-6, context.tile_size)
        max_tile_y = behavior.world_to_tile(oy + height - 1e-6, context.tile_size)

        for tx in range(min_tile_x, max_tile_x + 1):
            for ty in range(min_tile_y, max_tile_y + 1):
                tiles.add((tx, ty))
    return tiles
