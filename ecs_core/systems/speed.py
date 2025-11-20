from __future__ import annotations

import math

from ecs_core.components import Speed, Velocity


class SpeedSystem:
    """Clamp entity velocities so they always match their Speed component."""

    def __init__(self, world):
        self.world = world

    def update(self, dt: float):
        if dt is None:
            return
        for entity_id, spd, vel in self.world.view(Speed, Velocity):
            magnitude = math.hypot(vel.vx, vel.vy)
            if magnitude <= 1e-6:
                vel.vx = 0.0
                vel.vy = 0.0
                continue
            scale = spd.pixels_per_second / magnitude
            vel.vx *= scale
            vel.vy *= scale
