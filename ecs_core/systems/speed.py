from ecs_core.components.components import Position, Speed


class SpeedSystem:
    def __init__(self, world):
        self.world = world

    def update(self, dt: float):
        for eid, (pos, spd) in self.world.view(Position, Speed):
            # Formula: read speed as pixels per second
            dx, dy = (
                1.0,
                0.0,
            )  # Default direction (right); override per-entity if needed
            pos.x += dx * spd.pixels_per_second * dt
            pos.y += dy * spd.pixels_per_second * dt
