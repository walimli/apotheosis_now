import pygame
from ecs_core.systems_base import System
from ecs_core.components import Position, Renderable, Camera2DComponent


class RenderSystem(System):
    def __init__(self, screen, camera_entity_id, world):
        super().__init__(world)
        self.screen = screen
        self.camera_entity_id = camera_entity_id

    def update(self, dt):
        self.screen.fill((20, 20, 40))

        if self.camera_entity_id is None:
            raise RuntimeError("RenderSystem requires a camera entity to render the world.")

        camera_component = self.world.get(self.camera_entity_id, Camera2DComponent)
        if not camera_component:
            raise RuntimeError("Camera2DComponent missing from the registered camera entity.")

        camera_x = camera_component.rect.left
        camera_y = camera_component.rect.top

        # Render all entities with Position and Renderable components
        for entity, pos, rend in self.world.view(Position, Renderable):
            sx = pos.x - camera_x + self.screen.get_width() // 2
            sy = pos.y - camera_y + self.screen.get_height() // 2
            pygame.draw.circle(self.screen, rend.color, (int(sx), int(sy)), rend.radius)
