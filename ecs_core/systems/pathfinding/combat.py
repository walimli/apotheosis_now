from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, Tuple

from constants import TILE_SIZE
from ecs_core.systems.pathfinding import behavior

from .grid import AggressiveGridContext, TileCoord
from .planner import AggressivePathfinder, PathResult

Point = Tuple[float, float]
Size = Tuple[float, float]


@dataclass(frozen=True)
class AttackApproach:
    """Represents a planned approach tile and path for an aggressive mob."""

    goal_tile: TileCoord
    path: PathResult

    def requires_movement(self) -> bool:
        return not self.path.is_empty()


def plan_attack_approach(
    context: AggressiveGridContext,
    pathfinder: AggressivePathfinder,
    mob_center: Point,
    player_origin: Point,
    player_size: Size,
    *,
    avoid_tiles: Optional[Iterable[TileCoord]] = None,
    max_ring_radius: int = 2,
) -> Optional[AttackApproach]:
    """Choose a reachable tile near the player and plan a path toward it."""
    if max_ring_radius < 0:
        raise ValueError("max_ring_radius must be non-negative")

    avoid_frozen = frozenset(avoid_tiles or ())
    player_center = _player_center(player_origin, player_size)
    mob_tile = context.world_to_tile(*mob_center)

    direct_goal_tile = context.world_to_tile(*player_center)
    if direct_goal_tile not in avoid_frozen and context.is_walkable(direct_goal_tile):
        goal_world = context.tile_to_world_center(direct_goal_tile)
        direct_path = pathfinder.plan_path(
            mob_center,
            goal_world,
            avoid_tiles=avoid_frozen,
            reuse_cache=True,
        )
        if direct_path.tiles or direct_goal_tile == mob_tile:
            return AttackApproach(goal_tile=direct_goal_tile, path=direct_path)

    for ring in range(1, max_ring_radius + 1):
        candidates = list(_attack_ring_tiles(context, player_origin, player_size, ring))
        if not candidates:
            continue

        best_plan: Optional[AttackApproach] = None
        best_length: Optional[int] = None
        for tile in candidates:
            if tile in avoid_frozen:
                continue
            goal_world = context.tile_to_world_center(tile)
            path = pathfinder.plan_path(
                mob_center,
                goal_world,
                avoid_tiles=avoid_frozen,
                reuse_cache=False,
            )
            if not path.tiles and tile != mob_tile:
                continue
            length = len(path.tiles)
            if best_plan is None or length < best_length:
                best_plan = AttackApproach(goal_tile=tile, path=path)
                best_length = length
        if best_plan is not None:
            return best_plan

    return None


def _player_center(origin: Point, size: Size) -> Point:
    width = float(size[0]) if len(size) >= 1 and size[0] > 0 else float(TILE_SIZE)
    height = float(size[1]) if len(size) >= 2 and size[1] > 0 else float(TILE_SIZE)
    return (origin[0] + width * 0.5, origin[1] + height * 0.5)


def _attack_ring_tiles(
    context: AggressiveGridContext,
    player_origin: Point,
    player_size: Size,
    ring_radius: int,
) -> Iterator[TileCoord]:
    """Iterate walkable tiles forming a ring around the player's footprint."""
    if ring_radius <= 0:
        return

    tile_size = context.tile_size
    width = float(player_size[0]) if len(player_size) >= 1 and player_size[0] > 0 else float(tile_size)
    height = float(player_size[1]) if len(player_size) >= 2 and player_size[1] > 0 else float(tile_size)

    min_tile_x = behavior.world_to_tile(player_origin[0], tile_size)
    min_tile_y = behavior.world_to_tile(player_origin[1], tile_size)
    max_tile_x = behavior.world_to_tile(player_origin[0] + width - 1e-6, tile_size)
    max_tile_y = behavior.world_to_tile(player_origin[1] + height - 1e-6, tile_size)

    outer_min_x = min_tile_x - ring_radius
    outer_max_x = max_tile_x + ring_radius
    outer_min_y = min_tile_y - ring_radius
    outer_max_y = max_tile_y + ring_radius

    for tx in range(outer_min_x, outer_max_x + 1):
        for ty in range(outer_min_y, outer_max_y + 1):
            if min_tile_x <= tx <= max_tile_x and min_tile_y <= ty <= max_tile_y:
                continue  # Skip interior tiles occupied by the player
            on_perimeter = (
                tx == outer_min_x or tx == outer_max_x or ty == outer_min_y or ty == outer_max_y
            )
            if not on_perimeter:
                continue
            if context.is_walkable((tx, ty)):
                yield (tx, ty)


def should_force_replan(wait_steps: int, max_wait_steps: int) -> bool:
    """Return True when a stalled mob should abandon the current plan."""
    if max_wait_steps <= 0:
        return True
    return wait_steps >= max_wait_steps
