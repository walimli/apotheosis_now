from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

from .combat import AttackApproach, plan_attack_approach, should_force_replan
from .grid import AggressiveGridContext, TileCoord
from .planner import AggressivePathfinder, PathResult

Point = Tuple[float, float]
Size = Tuple[float, float]
Direction = Tuple[float, float]


@dataclass
class NavigationPlan:
    """Tracks progress along an attack approach path."""

    approach: AttackApproach
    waypoint_index: int = 0
    wait_steps: int = 0

    def current_waypoint(self) -> Optional[Point]:
        points = self.approach.path.world_points
        if not points:
            return None
        if self.waypoint_index >= len(points):
            return None
        return points[self.waypoint_index]

    def advance_if_reached(self, position: Point, tolerance: float) -> bool:
        waypoint = self.current_waypoint()
        if waypoint is None:
            return True
        dx = waypoint[0] - position[0]
        dy = waypoint[1] - position[1]
        if dx * dx + dy * dy <= tolerance * tolerance:
            self.waypoint_index += 1
            return True
        return False

    def reached_goal(self) -> bool:
        if self.approach.path.is_empty():
            return True
        return self.waypoint_index >= len(self.approach.path.world_points)


class AggressiveNavigator:
    """Controller-facing helper that steers aggressive mobs along planned paths."""

    def __init__(
        self,
        context: AggressiveGridContext,
        *,
        pathfinder: Optional[AggressivePathfinder] = None,
        waypoint_tolerance: float = 12.0,
        max_wait_steps: int = 2,
        max_ring_radius: int = 2,
    ) -> None:
        self._context = context
        self._pathfinder = pathfinder or AggressivePathfinder(context)
        self._tolerance = max(0.0, float(waypoint_tolerance))
        self._max_wait_steps = max_wait_steps
        self._max_ring_radius = max(0, int(max_ring_radius))
        self._plan: Optional[NavigationPlan] = None

    @property
    def plan(self) -> Optional[NavigationPlan]:
        return self._plan

    def invalidate(self) -> None:
        self._plan = None
        self._pathfinder.invalidate()

    def refresh_plan(
        self,
        mob_center: Point,
        mob_size: Size,
        player_origin: Point,
        player_size: Size,
        *,
        avoid_tiles: Optional[Iterable[TileCoord]] = None,
    ) -> Optional[NavigationPlan]:
        approach = plan_attack_approach(
            self._context,
            self._pathfinder,
            mob_center,
            player_origin,
            player_size,
            avoid_tiles=avoid_tiles,
            max_ring_radius=self._max_ring_radius,
        )
        if approach is None:
            self._plan = None
            return None
        self._plan = NavigationPlan(approach=approach)
        return self._plan

    def current_direction(self, mob_center: Point) -> Direction:
        plan = self._plan
        if plan is None:
            return (0.0, 0.0)
        waypoint = plan.current_waypoint()
        if waypoint is None:
            return (0.0, 0.0)
        dx = waypoint[0] - mob_center[0]
        dy = waypoint[1] - mob_center[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return (0.0, 0.0)
        return (dx / length, dy / length)

    def update_progress(
        self,
        mob_center: Point,
        *,
        moved_this_tick: bool,
    ) -> bool:
        """Update internal plan based on movement; return True if replan is recommended."""
        plan = self._plan
        if plan is None:
            return False

        advanced = plan.advance_if_reached(mob_center, self._tolerance)
        if plan.reached_goal():
            return False

        if advanced or moved_this_tick:
            plan.wait_steps = 0
            return False

        plan.wait_steps += 1
        if should_force_replan(plan.wait_steps, self._max_wait_steps):
            return True
        return False
