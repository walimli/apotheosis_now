from __future__ import annotations

from typing import Iterable, Optional, Tuple

import pygame

from ecs_core.components import Camera2DComponent, HitBox, Position
from ecs_core.components.collider import Collider
from ecs_core.systems_base import System


class HitBoxSystem(System):
    """Renders collider outlines for entities under the cursor."""

    def __init__(self, world, *, display, camera_entity: int):
        super().__init__(world)
        self.display = display
        self.camera_entity = camera_entity
        self._cursor_screen_pos: Optional[Tuple[int, int]] = None
        self._cursor_base_pos: Optional[Tuple[float, float]] = None
        self._cursor_world_pos: Optional[Tuple[float, float]] = None
        self._hovered_entities: set[int] = set()

    def update(self, dt: float) -> None:
        """Hit boxes are recomputed from events; no per-frame simulation."""
        _ = dt

    def handle_cursor_move(self, screen_pos: Optional[Tuple[int, int]]) -> None:
        """Accept a new cursor screen position and recompute hover state."""
        self._cursor_screen_pos = (
            (int(screen_pos[0]), int(screen_pos[1])) if screen_pos else None
        )
        self._cursor_base_pos = self._map_screen_to_base(self._cursor_screen_pos)
        self._cursor_world_pos = self._base_to_world(self._cursor_base_pos)
        self._refresh_hovered_entities()

    def handle_camera_updated(self) -> None:
        """Recalculate cursor world coordinates after a camera change."""
        if self._cursor_base_pos is None:
            return
        self._cursor_world_pos = self._base_to_world(self._cursor_base_pos)
        self._refresh_hovered_entities()

    def render(self, surface: pygame.Surface) -> None:
        """Draw hit box outlines for hovered entities."""
        if not self._hovered_entities:
            return
        camera = self.world.get(self.camera_entity, Camera2DComponent)
        if camera is None:
            return
        rect = camera.rect
        scale = float(camera.scale if camera.scale else 1.0)
        for entity in tuple(self._hovered_entities):
            position = self.world.get(entity, Position)
            collider = self.world.get(entity, Collider)
            component = self.world.get(entity, HitBox)
            if position is None or collider is None or component is None:
                self._hovered_entities.discard(entity)
                continue
            if not collider.enabled:
                continue
            center_x, center_y = _world_center(position, collider)
            screen_x = (center_x - rect.left) * scale
            screen_y = (center_y - rect.top) * scale
            radius = max(1, int(round((collider.diameter * 0.5) * scale)))
            color = component.color
            width = max(1, int(component.line_width))
            pygame.draw.circle(
                surface,
                color,
                (int(round(screen_x)), int(round(screen_y))),
                radius,
                width,
            )

    def hovered_entities(self) -> Iterable[int]:
        return tuple(self._hovered_entities)

    def _refresh_hovered_entities(self) -> None:
        cursor = self._cursor_world_pos
        if cursor is None:
            self._hovered_entities.clear()
            return
        hovered: set[int] = set()
        cursor_x, cursor_y = cursor
        for entity, position, collider, _hit_box in self.world.view(
            Position, Collider, HitBox
        ):
            if not collider.enabled:
                continue
            center_x, center_y = _world_center(position, collider)
            radius = collider.diameter * 0.5
            dx = cursor_x - center_x
            dy = cursor_y - center_y
            if dx * dx + dy * dy <= radius * radius:
                hovered.add(entity)
        self._hovered_entities = hovered

    def _map_screen_to_base(
        self, screen_pos: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[float, float]]:
        if screen_pos is None or self.display is None:
            return None
        scale, off_x, off_y = self.display.get_present_params()
        denom = max(1, int(scale))
        bx = (screen_pos[0] - off_x) / denom
        by = (screen_pos[1] - off_y) / denom
        return (bx, by)

    def _base_to_world(
        self, base_pos: Optional[Tuple[float, float]]
    ) -> Optional[Tuple[float, float]]:
        if base_pos is None:
            return None
        camera = self.world.get(self.camera_entity, Camera2DComponent)
        if camera is None:
            return None
        rect = camera.rect
        scale = float(camera.scale if camera.scale else 1.0)
        world_x = rect.left + base_pos[0] / scale
        world_y = rect.top + base_pos[1] / scale
        return (world_x, world_y)


def _world_center(position: Position, collider: Collider) -> Tuple[float, float]:
    base_x = position.render_x if position.render_x is not None else float(position.x)
    base_y = position.render_y if position.render_y is not None else float(position.y)
    return (base_x + collider.offset_x, base_y + collider.offset_y)
