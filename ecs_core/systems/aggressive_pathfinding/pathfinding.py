"""Integration layer between the legacy navigator stack and ECS components."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from ecs_core.components import AggressivePathfindingComponent, Collider, Position
from ecs_core.systems_base import System

from ecs_core.systems.pathfinding.grid import AggressiveGridContext
from ecs_core.systems.pathfinding.navigation import AggressiveNavigator
from ecs_core.systems.pathfinding.world_adapter import PathfindingWorldView

TileCoord = Tuple[int, int]
Point = Tuple[float, float]


@dataclass
class NavigatorState:
    navigator: AggressiveNavigator
    last_position: Optional[Point] = None
    last_player_tile: Optional[TileCoord] = None


class AggressivePathfindingManager(System):
    """Drives aggressive mobs by delegating to the legacy navigator stack."""

    def __init__(self, play_state) -> None:
        if play_state is None:
            raise ValueError("AggressivePathfindingManager requires a play_state")
        world = getattr(play_state, "ecs_world", None)
        if world is None:
            raise ValueError("play_state must expose ecs_world")
        super().__init__(world)

        self._world_renderer = getattr(play_state, "world_renderer", None)
        if self._world_renderer is None:
            raise ValueError("play_state.world_renderer is required")

        self._player_entity = getattr(play_state, "player_entity", None)
        self._world_view = PathfindingWorldView(self._world_renderer)
        self._grid_context = AggressiveGridContext.from_world(self._world_view)
        self._states: Dict[int, NavigatorState] = {}
        self._waypoint_tolerance = 14.0
        self._max_wait_steps = 3
        self._max_ring_radius = 2

    # ------------------------------------------------------------------ Public API
    def set_player_entity(self, entity_id: Optional[int]) -> None:
        self._player_entity = entity_id

    def register_entity(self, entity_id: int) -> None:
        self._ensure_state(entity_id)

    def unregister_entity(self, entity_id: int) -> None:
        self._states.pop(entity_id, None)

    # ---------------------------------------------------------------------- System
    def update(self, dt: float) -> None:
        if dt is None or dt <= 0.0:
            return

        player_bounds = self._player_bounds()
        if player_bounds is None:
            return
        player_center, player_origin, player_size, player_tile = player_bounds

        active: set[int] = set()
        for entity_id, component, position in self.world.view(
            AggressivePathfindingComponent, Position
        ):
            active.add(entity_id)
            direction = self._update_entity(
                entity_id,
                component,
                position,
                player_center,
                player_origin,
                player_size,
                player_tile,
            )
            component.dir_x, component.dir_y = direction

        stale = [entity_id for entity_id in self._states.keys() if entity_id not in active]
        for entity_id in stale:
            self._states.pop(entity_id, None)

    # ------------------------------------------------------------------ Internals
    def _ensure_state(self, entity_id: int) -> NavigatorState:
        state = self._states.get(entity_id)
        if state is None:
            navigator = AggressiveNavigator(
                self._grid_context,
                waypoint_tolerance=self._waypoint_tolerance,
                max_wait_steps=self._max_wait_steps,
                max_ring_radius=self._max_ring_radius,
            )
            state = NavigatorState(navigator=navigator)
            self._states[entity_id] = state
        return state

    def _update_entity(
        self,
        entity_id: int,
        component: AggressivePathfindingComponent,
        position: Position,
        player_center: Point,
        player_origin: Point,
        player_size: Tuple[float, float],
        player_tile: TileCoord,
    ) -> Tuple[float, float]:
        state = self._ensure_state(entity_id)
        navigator = state.navigator
        mob_center = (float(position.x), float(position.y))

        moved = False
        if state.last_position is not None:
            dx = mob_center[0] - state.last_position[0]
            dy = mob_center[1] - state.last_position[1]
            moved = (dx * dx + dy * dy) >= 1.0
        state.last_position = mob_center

        mob_size = self._resolve_entity_size(entity_id)
        player_tile_changed = state.last_player_tile != player_tile
        if player_tile_changed:
            state.last_player_tile = player_tile
            navigator.invalidate()

        plan_missing = navigator.plan is None
        if plan_missing or player_tile_changed:
            navigator.refresh_plan(
                mob_center,
                mob_size,
                player_origin,
                player_size,
            )
        elif navigator.update_progress(mob_center, moved_this_tick=moved):
            navigator.refresh_plan(
                mob_center,
                mob_size,
                player_origin,
                player_size,
            )

        direction = navigator.current_direction(mob_center)
        if self._is_zero(direction):
            direction = self._vector_to_target(mob_center, player_center)
        return direction

    def _player_bounds(
        self,
    ) -> Optional[Tuple[Point, Point, Tuple[float, float], TileCoord]]:
        if self._player_entity is None:
            return None
        position = self.world.get(self._player_entity, Position)
        if position is None:
            return None
        collider = self.world.get(self._player_entity, Collider)
        width = float(collider.diameter) if collider else float(self._world_view.tile_size)
        height = width
        offset_x = float(getattr(collider, "offset_x", 0.0)) if collider else 0.0
        offset_y = float(getattr(collider, "offset_y", 0.0)) if collider else 0.0
        center = (float(position.x), float(position.y))
        origin = (center[0] + offset_x - width * 0.5, center[1] + offset_y - height * 0.5)
        tile = self._grid_context.world_to_tile(*center)
        return center, origin, (width, height), tile

    def _resolve_entity_size(self, entity_id: int) -> Tuple[float, float]:
        collider = self.world.get(entity_id, Collider)
        if collider:
            return (float(collider.diameter), float(collider.diameter))
        return (float(self._world_view.tile_size), float(self._world_view.tile_size))

    def _vector_to_target(self, start: Point, target: Point) -> Tuple[float, float]:
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 1e-6:
            return (0.0, 0.0)
        return (dx / length, dy / length)

    @staticmethod
    def _is_zero(vector: Tuple[float, float]) -> bool:
        return abs(vector[0]) < 1e-5 and abs(vector[1]) < 1e-5

