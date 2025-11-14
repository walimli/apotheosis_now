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
        self.screen.fill((20, 20, 40))

        if self.camera_entity_id is None:
            raise RuntimeError("RenderSystem requires a camera entity to render the world.")

        camera_component = self.world.get(self.camera_entity_id, Camera2DComponent)
        if not camera_component:
            raise RuntimeError("Camera2DComponent missing from the registered camera entity.")

        camera_x = camera_component.rect.left
        camera_y = camera_component.rect.top

        self._render_basic_primitives(camera_x, camera_y)
        self._render_sprite_entities(camera_x, camera_y)

    def _render_basic_primitives(self, camera_x: int, camera_y: int) -> None:
        for _entity, pos, rend in self.world.view(Position, Renderable):
            sx = pos.x - camera_x + self.screen.get_width() // 2
            sy = pos.y - camera_y + self.screen.get_height() // 2
            pygame.draw.circle(self.screen, rend.color, (int(sx), int(sy)), rend.radius)

    def _render_sprite_entities(self, camera_x: int, camera_y: int) -> None:
        width_half = self.screen.get_width() // 2
        height_half = self.screen.get_height() // 2
        for _entity, pos, sprite in self.world.view(Position, RenderableEntityComponent):
            surface = self._get_sprite_surface(sprite)
            if surface is None:
                continue

            draw_x = pos.x - camera_x + width_half + sprite.offset[0]
            draw_y = pos.y - camera_y + height_half + sprite.offset[1]
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
