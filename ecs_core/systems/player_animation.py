from __future__ import annotations

from typing import Tuple

import pygame

from ecs_core.components import Camera2DComponent, PlayerAnimationHandle, Position
from ecs_core.systems_base import System


class PlayerAnimationSystem(System):
    """Bridges the legacy player animation service into the ECS render/update loop."""

    def __init__(self, world, camera_entity: int):
        super().__init__(world)
        self.camera_entity = camera_entity

    def update(self, dt: float) -> None:
        for _entity, position, handle in self.world.view(Position, PlayerAnimationHandle):
            service = getattr(handle, "service", None)
            if service is None:
                continue
            service.set_position(_world_pos(position))
            service.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        camera = self.world.get(self.camera_entity, Camera2DComponent)
        if camera is None:
            return
        rect = camera.rect
        for _entity, position, handle in self.world.view(Position, PlayerAnimationHandle):
            service = getattr(handle, "service", None)
            if service is None:
                continue
            frame, offset = service.current_surface()
            world_x, world_y = _world_pos(position)
            draw_x = (world_x - rect.left) + offset[0]
            draw_y = (world_y - rect.top) + offset[1]
            surface.blit(frame, (int(round(draw_x)), int(round(draw_y))))


def _world_pos(position: Position) -> Tuple[float, float]:
    base_x = position.render_x if position.render_x is not None else float(position.x)
    base_y = position.render_y if position.render_y is not None else float(position.y)
    return base_x, base_y
