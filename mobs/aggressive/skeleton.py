from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import pygame

from systems.audio_package import publish_audio_event
from systems.asset_loader.mob_assets import MobAssetProvider
from systems.mobs.core import behavior
from systems.mobs.aggressive.pathfinding import (
    AggressiveGridContext,
    AggressiveNavigator,
)
from systems.mobs.core.base_view import BaseMobView
from systems.mobs.core.collision_helpers import CollisionHandle
from systems.mobs.core.species_loader import MobSpec

from constants import TILE_SIZE
ATTACK_STATE_TIME = 13.0 / 12.0  # seconds (13 frames at ~12 fps)
HIT_STATE_TIME = 5.0 / 12.0  # seconds (5 frames at ~12 fps)
DIE_STATE_TIME = 6.0 / 8.0  # seconds (6 frames at ~8 fps)


@dataclass
class SkeletonModel:
    id: int
    species_id: str
    x: float
    y: float
    hp_max: int
    hp_cur: int
    speed_px_s: float
    attack_range_px: float
    attack_damage: int
    attack_cooldown_s: float
    cooldown_left: float = 0.0
    facing: str = "down"
    body_radius_px: float = 20.0
    state: str = "idle"
    state_timer: float = 0.0
    is_dead: bool = False
    is_moving: bool = False
    _xp_granted: bool = False

    @property
    def pos(self) -> Tuple[float, float]:
        return (self.x, self.y)


class SkeletonController:
    def __init__(
        self,
        model: SkeletonModel,
        footprint_px: Tuple[float, float] = (64.0, 64.0),
        collider_rect_px: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        self.m = model
        self._footprint = (float(footprint_px[0]), float(footprint_px[1]))
        self._move_dir: Tuple[float, float] = (0.0, 0.0)
        if collider_rect_px is None:
            width, height = self._footprint
            offset_x = (self._footprint[0] - width) / 2.0
            offset_y = self._footprint[1] - height
        else:
            width, height, offset_x, offset_y = collider_rect_px
        self._collider_size = (float(width), float(height))
        self._collider_offset = (float(offset_x), float(offset_y))
        self._collision_handle = CollisionHandle(
            width=self._collider_size[0],
            height=self._collider_size[1],
            offset_x=self._collider_offset[0],
            offset_y=self._collider_offset[1],
        )
        self._grid_context: Optional[AggressiveGridContext] = None
        self._navigator: Optional[AggressiveNavigator] = None
        self._world_ref = None
        self._last_target_tile: Optional[Tuple[int, int]] = None

    def update(self, dt: float, player, world=None) -> None:
        if world is None:
            raise ValueError("SkeletonController.update requires a world for navigation")

        if self.m.state_timer > 0.0:
            self.m.state_timer = max(0.0, self.m.state_timer - dt)
            if self.m.state_timer <= 1e-6 and self.m.state in {"attack", "hit"}:
                self._reset_to_movement_state()

        if self.m.cooldown_left > 0.0:
            self.m.cooldown_left = max(0.0, self.m.cooldown_left - dt)

        player_model = getattr(player, "model")
        player_pos = getattr(player, "world_pos")
        player_w = float(getattr(player_model, "w"))
        player_h = float(getattr(player_model, "h"))
        target_center = behavior.entity_center(player_pos, player_w, player_h)

        self._ensure_navigation(world)
        grid_context = self._grid_context
        navigator = self._navigator
        if grid_context is None or navigator is None:
            raise RuntimeError("Skeleton navigation failed to initialize")
        if not self.m.is_dead:
            self._collision_handle.ensure_attached(world)
            self._collision_handle.update_from_entity_position(self.m.x, self.m.y)
        else:
            self._collision_handle.detach()

        mob_center = behavior.entity_center((self.m.x, self.m.y), *self._footprint)
        dx = target_center[0] - mob_center[0]
        dy = target_center[1] - mob_center[1]
        dist = math.hypot(dx, dy)

        if abs(dx) > abs(dy):
            self.m.facing = "right" if dx > 0 else "left"
        else:
            self.m.facing = "down" if dy > 0 else "up"

        can_move = self.m.state not in {"attack", "hit", "die"} and not self.m.is_dead
        moving = False
        if can_move and dist > 1e-3:
            player_tile = grid_context.world_to_tile(*target_center)
            if navigator.plan is None or self._last_target_tile != player_tile:
                plan = navigator.refresh_plan(
                    mob_center,
                    self._footprint,
                    player_pos,
                    (player_w, player_h),
                    avoid_tiles=self._collect_avoid_tiles(),
                )
                self._last_target_tile = player_tile if plan is not None else None

            desired_dir = navigator.current_direction(mob_center)
            self._move_dir = behavior.normalize(desired_dir)

            if self._move_dir != (0.0, 0.0):
                vx = self._move_dir[0] * self.m.speed_px_s * dt
                vy = self._move_dir[1] * self.m.speed_px_s * dt
                old_x, old_y = self.m.x, self.m.y
                self.m.x, self.m.y = self._collision_handle.resolve_move(
                    entity_x=self.m.x,
                    entity_y=self.m.y,
                    delta_x=vx,
                    delta_y=vy,
                )
                moved_distance = math.hypot(self.m.x - old_x, self.m.y - old_y)
                moving = moved_distance > 1e-3

        new_center = behavior.entity_center((self.m.x, self.m.y), *self._footprint)
        if navigator.update_progress(new_center, moved_this_tick=moving):
            navigator.invalidate()
            self._last_target_tile = None

        self.m.is_moving = moving and not self.m.is_dead

        if can_move:
            self.m.state = "run" if self.m.is_moving else "idle"

        if (
            not self.m.is_dead
            and dist <= self.m.attack_range_px
            and self.m.cooldown_left <= 1e-6
            and self.m.state not in {"attack", "hit", "die"}
        ):
            self._begin_attack(player)

    def register_hit(self, lethal: bool) -> None:
        if self.m.is_dead and self.m.state == "die":
            return
        if lethal:
            if self.m.is_dead and self.m.state == "die":
                return
            self.m.is_dead = True
            self.m.is_moving = False
            self.m.state = "die"
            self.m.state_timer = DIE_STATE_TIME
            self._collision_handle.detach()
        else:
            self.m.is_moving = False
            self.m.state = "hit"
            self.m.state_timer = HIT_STATE_TIME

    def should_despawn(self) -> bool:
        return self.m.is_dead and self.m.state == "die" and self.m.state_timer <= 1e-6

    def _begin_attack(self, player) -> None:
        self.m.state = "attack"
        self.m.state_timer = ATTACK_STATE_TIME
        self.m.cooldown_left = self.m.attack_cooldown_s

        publish_audio_event("mob.attack")
        player_model = getattr(player, "model")
        ph = getattr(player_model, "health")
        ph.take_damage(self.m.attack_damage)

    def _reset_to_movement_state(self) -> None:
        if self.m.is_dead:
            self.m.state = "die"
            return
        self.m.state = "run" if self.m.is_moving else "idle"


    def _ensure_navigation(self, world) -> None:
        if self._grid_context is None or self._world_ref is not world:
            self._grid_context = AggressiveGridContext.from_world(world)
            self._navigator = AggressiveNavigator(self._grid_context)
            self._world_ref = world
            self._last_target_tile = None
        elif self._navigator is None:
            self._navigator = AggressiveNavigator(self._grid_context)
            self._last_target_tile = None

    def _collect_avoid_tiles(self):
        return None

class SkeletonView(BaseMobView):
    FPS_BY_ACTION = {
        "idle": 6.0,
        "run": 10.0,
        "attack": 12.0,
        "hit": 12.0,
        "die": 8.0,
    }

    STATE_PRIORITY = ("die", "hit", "attack", "run", "idle")

    def __init__(
        self,
        model: SkeletonModel,
        assets: MobAssetProvider,
        groups: Dict[str, str],
        frame_size: Tuple[int, int],
        z_index: int,
    ) -> None:
        super().__init__(model, footprint_px=frame_size, z_index=z_index)
        self.assets = assets
        self.groups = groups
        self._timer = 0.0
        self._last_state: Optional[str] = None
        self._last_facing: Optional[str] = None

    def update(self, dt: float) -> None:
        state = getattr(self.m, "state", "idle")
        facing = getattr(self.m, "facing", "down")
        if state != self._last_state or facing != self._last_facing:
            self._timer = 0.0
            self._last_state = state
            self._last_facing = facing
        else:
            self._timer += dt

    def _current_frame(self) -> Optional[pygame.Surface]:
        facing = getattr(self.m, "facing", "down")
        state = getattr(self.m, "state", "idle")
        moving = getattr(self.m, "is_moving", False)

        candidates = []
        if state == "die":
            candidates.append("die")
        elif state == "hit":
            candidates.extend(["hit", "attack"])
        elif state == "attack":
            candidates.append("attack")

        if state not in {"die", "hit", "attack"}:
            candidates.append("run" if moving else "idle")

        candidates.extend(["run", "idle"])

        for action in candidates:
            key = self._resolve_group(action, facing)
            if not key:
                continue
            frames = self.assets.get_frames(key)
            if not frames:
                continue
            fps = self.FPS_BY_ACTION.get(action, 8.0)
            index = int(self._timer * fps) % len(frames)
            return frames[index]
        return None

    def _resolve_group(self, action: str, facing: str) -> Optional[str]:
        primary = self.groups.get(f"{action}_{facing}")
        if primary:
            return primary
        if action == "run":
            fallback = self.groups.get(f"walk_{facing}")
            if fallback:
                return fallback
        if action == "idle":
            fallback = self.groups.get(f"walk_{facing}")
            if fallback:
                return fallback
        return None


def create_skeleton(
    next_id: int,
    spec: MobSpec,
    spawn_pos_px: Tuple[float, float],
    assets: MobAssetProvider,
):
    m = SkeletonModel(
        id=next_id,
        species_id=spec.id,
        x=float(spawn_pos_px[0]),
        y=float(spawn_pos_px[1]),
        hp_max=int(spec.stats.durability),
        hp_cur=int(spec.stats.durability),
        speed_px_s=float(spec.stats.speed_px_per_s),
        attack_range_px=float(spec.stats.attack_range_px),
        attack_damage=int(spec.stats.attack_damage),
        attack_cooldown_s=float(spec.stats.attack_cooldown_s),
        body_radius_px=float(32.0 * spec.collider.capsule.width_tiles),
    )
    footprint = (float(spec.assets.frame_width), float(spec.assets.frame_height))
    collider_def = getattr(spec, "collider", None)
    collider_rect = None
    if collider_def is not None and hasattr(collider_def, "aabb"):
        aabb = collider_def.aabb
        width_px = float(aabb.width_tiles * TILE_SIZE)
        height_px = float(aabb.height_tiles * TILE_SIZE)
        anchor = getattr(collider_def, "anchor", "feet")
        if anchor == "feet":
            base_offset_x = (footprint[0] - width_px) / 2.0
            base_offset_y = footprint[1] - height_px
        else:
            base_offset_x = (footprint[0] - width_px) / 2.0
            base_offset_y = (footprint[1] - height_px) / 2.0
        offset_x = base_offset_x + float(aabb.offset_x_tiles * TILE_SIZE)
        offset_y = base_offset_y + float(aabb.offset_y_tiles * TILE_SIZE)
        collider_rect = (width_px, height_px, offset_x, offset_y)
    c = SkeletonController(m, footprint_px=footprint, collider_rect_px=collider_rect)
    v = SkeletonView(
        m,
        assets,
        spec.assets.registry_group_keys,
        (spec.assets.frame_width, spec.assets.frame_height),
        int(getattr(spec, "z_index", 0)),
    )
    return m, c, v




