from __future__ import annotations

import random
from typing import Optional, Tuple

from systems.mobs.core import behavior
from systems.mobs.core.collision_helpers import CollisionHandle
from systems.time_manager_package.time_events import TimeEventType
from .model import WispModel
from .push import compute_push_delta


class WispController:
    def __init__(
        self,
        model: WispModel,
        *,
        footprint_px: Tuple[float, float],
        collider_rect_px: Tuple[float, float, float, float],
    ) -> None:
        self.m = model
        self._footprint = (float(footprint_px[0]), float(footprint_px[1]))
        width, height, offset_x, offset_y = collider_rect_px
        self._collider_size = (float(width), float(height))
        self._collider_offset = (float(offset_x), float(offset_y))
        self._collision_handle = CollisionHandle(
            width=self._collider_size[0],
            height=self._collider_size[1],
            offset_x=self._collider_offset[0],
            offset_y=self._collider_offset[1],
        )
        self._wander_target: Optional[Tuple[float, float]] = None
        self._stun_timer: float = 0.0
        self._last_player_center: Optional[Tuple[float, float]] = None

    def update(self, dt: float, player, world=None) -> None:
        if world is None:
            raise ValueError("WispController.update requires world instance")

        if self.m.is_dead:
            self.m.is_moving = False
            self._wander_target = None
            self._collision_handle.detach()
            return

        if self._stun_timer > 0.0:
            self._stun_timer = max(0.0, self._stun_timer - dt)

        self._collision_handle.ensure_attached(world)
        self._collision_handle.update_from_entity_position(self.m.x, self.m.y)

        vx, vy = 0.0, 0.0
        if self._wander_target is not None and self._stun_timer <= 0.0:
            wx, wy = self._wander_target
            dx = wx - self.m.x
            dy = wy - self.m.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= 1.0:
                self._wander_target = None
            else:
                dir_x, dir_y = dx / dist, dy / dist
                speed = float(self.m.speed_px_s)
                vx += dir_x * speed * dt
                vy += dir_y * speed * dt

        (push_dx, push_dy), new_center = compute_push_delta(
            player,
            last_player_center=self._last_player_center,
            wisp_x=self.m.x,
            wisp_y=self.m.y,
            collider_size=self._collider_size,
            collider_offset=self._collider_offset,
            wisp_speed_px_s=self.m.speed_px_s,
            dt=dt,
        )
        self._last_player_center = new_center
        vx += push_dx
        vy += push_dy

        moved = False
        if abs(vx) > 1e-6 or abs(vy) > 1e-6:
            nx, ny = self._collision_handle.resolve_move(
                entity_x=self.m.x,
                entity_y=self.m.y,
                delta_x=vx,
                delta_y=vy,
            )
            moved = (abs(nx - self.m.x) > 1e-4) or (abs(ny - self.m.y) > 1e-4)
            self.m.x = nx
            self.m.y = ny
            if self._wander_target is not None:
                tx, ty = self._wander_target
                if abs(nx - tx) <= 1.0 and abs(ny - ty) <= 1.0:
                    self._wander_target = None
            if moved:
                self._update_facing(vx, vy)
        self.m.is_moving = moved

    def register_hit(self, lethal: bool) -> None:
        if self.m.is_dead:
            return
        if lethal:
            self.m.is_dead = True
            self.m.is_moving = False
            self._wander_target = None
            self._collision_handle.detach()
        else:
            self._stun_timer = 0.25

    def should_despawn(self) -> bool:
        return bool(self.m.is_dead)

    def handle_time_event(self, event, world=None) -> None:
        if getattr(event, "event_type", None) is TimeEventType.GAME_HOUR_PASSED:
            self._queue_random_wander(world)

    # --- Internal helpers -------------------------------------------------
    def _queue_random_wander(self, world) -> None:
        if world is None or self.m.is_dead:
            return
        tile_size = getattr(world, "tile_size", None)
        if tile_size is None:
            tile_size = getattr(world, "TILE_SIZE", None)
        if tile_size is None:
            tile_size = 32

        current_center = behavior.entity_center((self.m.x, self.m.y), *self._footprint)

        tile_x = behavior.world_to_tile(current_center[0], tile_size)
        tile_y = behavior.world_to_tile(current_center[1], tile_size)

        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        random.shuffle(directions)

        for dx, dy in directions:
            candidate_x = self.m.x + dx * tile_size
            candidate_y = self.m.y + dy * tile_size
            if not behavior.can_spawn_at(
                world,
                (candidate_x, candidate_y),
                width=self._footprint[0],
                height=self._footprint[1],
            ):
                continue
            self._wander_target = (candidate_x, candidate_y)
            break

    def _update_facing(self, dx: float, dy: float) -> None:
        if abs(dx) <= 1e-6 and abs(dy) <= 1e-6:
            return
        if abs(dx) > abs(dy):
            self.m.facing = "right" if dx > 0 else "left"
        else:
            self.m.facing = "down" if dy > 0 else "up"

