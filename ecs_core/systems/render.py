import pygame
from ecs_core.systems_base import System
from ecs_core.components.components import Position, Renderable


class RenderSystem(System):
    def __init__(self, screen, camera, world):
        super().__init__(world)
        self.screen = screen
        self.camera = camera

    def update(self, dt):
        self.screen.fill((20, 20, 40))
        for eid, (pos, rend) in self.world.view(Position, Renderable):
            sx = pos.x - self.camera[0] + self.screen.get_width() // 2
            sy = pos.y - self.camera[1] + self.screen.get_height() // 2
            pygame.draw.circle(self.screen, rend.color, (int(sx), int(sy)), rend.radius)
