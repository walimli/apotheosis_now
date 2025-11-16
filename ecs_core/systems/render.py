import pygame
from pathlib import Path
from typing import Dict, Optional, Tuple

from ecs_core.systems_base import System
from ecs_core.components import (
    Camera2DComponent,
    Position,
    Renderable,
)
from ecs_core.components.rendering_components import RenderableEntityComponent


class RenderSystem(System):
    def __init__(self, screen, camera_entity_id, world):
        super().__init__(world)
        self.screen = screen
        self.camera_entity_id = camera_entity_id
        self._sprite_cache: Dict[str, pygame.Surface] = {}
        self._scaled_cache: Dict[Tuple[str, Optional[Tuple[int, int]], float], pygame.Surface] = {}

    def update(self, dt):
        if self.camera_entity_id is None:
            raise RuntimeError("RenderSystem requires a camera entity to render the world.")

        camera_component = self.world.get(self.camera_entity_id, Camera2DComponent)
        if not camera_component:
            raise RuntimeError("Camera2DComponent missing from the registered camera entity.")

        camera_rect = camera_component.rect
        camera_x = camera_rect.left
        camera_y = camera_rect.top

        self._render_basic_primitives(camera_x, camera_y)
        self._render_sprite_entities(camera_x, camera_y)

    def _render_basic_primitives(self, camera_x: int, camera_y: int) -> None:
        for _entity, pos, rend in self.world.view(Position, Renderable):
            base_x = pos.render_x if pos.render_x is not None else float(pos.x)
            base_y = pos.render_y if pos.render_y is not None else float(pos.y)
            sx = base_x - camera_x
            sy = base_y - camera_y
            pygame.draw.circle(self.screen, rend.color, (int(sx), int(sy)), rend.radius)

    def _render_sprite_entities(self, camera_x: int, camera_y: int) -> None:
        for _entity, pos, sprite in self.world.view(Position, RenderableEntityComponent):
            surface = self._get_sprite_surface(sprite)
            if surface is None:
                continue

            base_x = pos.render_x if pos.render_x is not None else float(pos.x)
            base_y = pos.render_y if pos.render_y is not None else float(pos.y)
            draw_x = base_x - camera_x + sprite.offset[0]
            draw_y = base_y - camera_y + sprite.offset[1]
            origin_x = draw_x - surface.get_width() * sprite.anchor[0]
            origin_y = draw_y - surface.get_height() * sprite.anchor[1]
            self.screen.blit(surface, (int(origin_x), int(origin_y)))

    def _get_sprite_surface(
        self, component: RenderableEntityComponent
    ) -> Optional[pygame.Surface]:
        if not component.sprite_path:
            return None

        base_surface = self._load_sprite(component.sprite_path)
        if base_surface is None:
            return None

        cache_key = (component.sprite_path, component.size, component.scale)
        if cache_key in self._scaled_cache:
            return self._scaled_cache[cache_key]

        surface = base_surface
        if component.size:
            surface = pygame.transform.smoothscale(base_surface, component.size)
        elif component.scale != 1.0:
            width = max(1, int(base_surface.get_width() * component.scale))
            height = max(1, int(base_surface.get_height() * component.scale))
            surface = pygame.transform.smoothscale(base_surface, (width, height))

        self._scaled_cache[cache_key] = surface
        return surface

    def _load_sprite(self, path: str) -> Optional[pygame.Surface]:
        cache_key = str(Path(path))
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]

        sprite_path = Path(path)
        if not sprite_path.is_file():
            return None

        try:
            surface = pygame.image.load(sprite_path.as_posix()).convert_alpha()
        except pygame.error:
            return None

        self._sprite_cache[cache_key] = surface
        return surface
