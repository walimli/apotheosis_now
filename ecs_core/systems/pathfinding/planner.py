from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from .grid import AggressiveGridContext, TileCoord

Point = Tuple[float, float]


@dataclass(frozen=True)
class PathResult:
    """Container for an immutable planned path."""

    tiles: Tuple[TileCoord, ...]
    world_points: Tuple[Point, ...]

    def is_empty(self) -> bool:
        return not self.tiles


class AggressivePathfinder:
    """A* planner with caching tailored for aggressive mobs."""

    def __init__(self, context: AggressiveGridContext) -> None:
        self._context = context
        self._cached_start: Optional[TileCoord] = None
        self._cached_goal: Optional[TileCoord] = None
        self._cached_avoid: Optional[frozenset[TileCoord]] = None
        self._cached_path: Optional[PathResult] = None

    def plan_path(
        self,
        start_world: Point,
        goal_world: Point,
        *,
        avoid_tiles: Optional[Iterable[TileCoord]] = None,
        reuse_cache: bool = True,
    ) -> PathResult:
        """Compute (or reuse) the shortest path from start to goal."""
        start_tile = self._context.world_to_tile(*start_world)
        goal_tile = self._context.world_to_tile(*goal_world)
        avoid_frozen = frozenset(avoid_tiles or ())

        if reuse_cache and self._can_reuse(start_tile, goal_tile, avoid_frozen):
            cached = self._cached_path
            if cached is not None:
                return cached

        path_tiles = self._compute_path(start_tile, goal_tile, avoid_frozen)
        world_points = tuple(
            self._context.tile_to_world_center(tile) for tile in path_tiles
        )
        result = PathResult(path_tiles, world_points)

        self._cached_start = start_tile
        self._cached_goal = goal_tile
        self._cached_avoid = avoid_frozen
        self._cached_path = result
        return result

    def invalidate(self) -> None:
        """Clear any cached path so the next call recomputes."""
        self._cached_start = None
        self._cached_goal = None
        self._cached_avoid = None
        self._cached_path = None

    def _can_reuse(
        self,
        start_tile: TileCoord,
        goal_tile: TileCoord,
        avoid_frozen: frozenset[TileCoord],
    ) -> bool:
        if self._cached_path is None:
            return False
        if start_tile != self._cached_start or goal_tile != self._cached_goal:
            return False
        if avoid_frozen != (self._cached_avoid or frozenset()):
            return False
        return self._path_still_walkable(self._cached_path.tiles, goal_tile)

    def _path_still_walkable(
        self,
        tiles: Sequence[TileCoord],
        goal: TileCoord,
    ) -> bool:
        for tile in tiles:
            if tile == goal:
                continue
            if not self._context.is_walkable(tile):
                return False
        return True

    def _compute_path(
        self,
        start: TileCoord,
        goal: TileCoord,
        avoid_tiles: frozenset[TileCoord],
    ) -> Tuple[TileCoord, ...]:
        if start == goal:
            return ()

        open_heap: List[Tuple[float, TileCoord]] = []
        heapq.heappush(open_heap, (0.0, start))

        came_from: dict[TileCoord, Optional[TileCoord]] = {start: None}
        g_score: dict[TileCoord, float] = {start: 0.0}

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current == goal:
                return self._reconstruct_path(came_from, current, start)

            for neighbor in self._neighbors(current, goal, avoid_tiles):
                tentative_g = g_score[current] + 1.0
                if tentative_g >= g_score.get(neighbor, float("inf")):
                    continue
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + self._heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f_score, neighbor))

        return ()

    def _neighbors(
        self,
        tile: TileCoord,
        goal: TileCoord,
        avoid_tiles: frozenset[TileCoord],
    ) -> Sequence[TileCoord]:
        tx, ty = tile
        neighbors = (
            (tx, ty - 1),
            (tx + 1, ty),
            (tx, ty + 1),
            (tx - 1, ty),
        )

        result: List[TileCoord] = []
        for neighbor in neighbors:
            if neighbor in avoid_tiles and neighbor != goal:
                continue
            if self._context.is_walkable(neighbor) or neighbor == goal:
                result.append(neighbor)
        return result

    def _heuristic(self, tile: TileCoord, goal: TileCoord) -> float:
        return float(abs(tile[0] - goal[0]) + abs(tile[1] - goal[1]))

    def _reconstruct_path(
        self,
        came_from: dict[TileCoord, Optional[TileCoord]],
        current: TileCoord,
        start: TileCoord,
    ) -> Tuple[TileCoord, ...]:
        path: List[TileCoord] = []
        while current != start:
            path.append(current)
            parent = came_from.get(current)
            if parent is None:
                break
            current = parent
        path.reverse()
        return tuple(path)
