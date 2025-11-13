"""ECS system powering the shader-based void background."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

import pygame
from ecs_core.systems_base import System
from ecs_core.components.rendering_components import (
    Camera2DComponent,
    VoidVisualComponent,
)

from .void_render_pass import VoidRenderPass


class VoidRenderSystem(System):
    def __init__(
        self, world, *, target_surface: Optional[pygame.Surface] = None
    ) -> None:
        super().__init__(world)
        self._target_surface = target_surface
        self._void_pass = VoidRenderPass()
        self._last_update_ms: Optional[int] = None

    def set_target_surface(self, surface: pygame.Surface | None) -> None:
        self._target_surface = surface

    def update(self, dt: float | None = None) -> None:
        if self._target_surface is None:
            return
        if dt is None:
            now = pygame.time.get_ticks()
            if self._last_update_ms is None:
                dt = 0.0
            else:
                dt = (now - self._last_update_ms) / 1000.0
            self._last_update_ms = now
        for entity, camera, visual in self.world.view(
            Camera2DComponent, VoidVisualComponent
        ):
            new_scroll = (
                visual.scroll_position[0] + visual.scroll_speed[0] * dt,
                visual.scroll_position[1] + visual.scroll_speed[1] * dt,
            )
            updated = replace(
                visual,
                scroll_position=new_scroll,
                time_offset=visual.time_offset + dt,
            )
            self.world.add(entity, updated)
            self._void_pass.render(
                self._target_surface,
                camera,
                updated,
            )

    def release(self) -> None:
        self._void_pass.release()


__all__ = ["VoidRenderSystem"]
