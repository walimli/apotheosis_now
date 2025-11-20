"""Ghost state handling for fence placement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple

import pygame

from constants import PLAYER_FEET_H, PLAYER_FEET_W, PLAYER_SIZE

from . import data, grid
from .geometry import aabb_from_points, aabb_overlap, transform_local64_to_world

Vec2f = Tuple[float, float]
TileCoord = Tuple[int, int]


@dataclass
class GhostSelection:
    variant_key: str
    tile: TileCoord
    world_center: Vec2f


class FenceGhost:
    """Manage ghost state, variant choice, and validity checks."""

    def __init__(self, world, collision_system, placed_manager) -> None:
        self.world = world
        self.collision = collision_system
        self.placed = placed_manager
        self.active: bool = False
        self._current_tile: Optional[TileCoord] = None
        self._variant_pool: List[str] = []
        self._variant_index: int = 0
        self.selection: Optional[GhostSelection] = None
        self.tint_valid = (90, 140, 255, 150)
        self.tint_invalid = (255, 90, 90, 150)
        self.player = None
        self._validator: Optional[Callable[[GhostSelection], bool]] = None

    # --- State management ---
    def activate(
        self,
        tile: TileCoord,
        variant_pool: Iterable[str],
        preferred: Optional[str] = None,
    ) -> None:
        self.active = True
        self._current_tile = tile
        self.update_variant_pool(variant_pool, preferred=preferred)

    def deactivate(self) -> None:
        self.active = False
        self._current_tile = None
        self._variant_pool = []
        self._variant_index = 0
        self.selection = None
        self.player = None

    def cycle_variant(self, delta: int) -> None:
        if not self._variant_pool:
            return
        self._variant_index = (self._variant_index + delta) % len(self._variant_pool)
        self._refresh_selection()

    def update_variant_pool(
        self, variant_pool: Iterable[str], preferred: Optional[str] = None
    ) -> None:
        pool = list(dict.fromkeys(variant_pool))
        if not pool:
            self.selection = None
            self._variant_pool = []
            return
        if preferred and preferred in pool:
            pool.remove(preferred)
            pool.insert(0, preferred)
        self._variant_pool = pool
        if self.selection and self.selection.variant_key in pool:
            self._variant_index = pool.index(self.selection.variant_key)
        else:
            self._variant_index = 0
        self._refresh_selection()

    def _refresh_selection(self) -> None:
        if not self.active or not self._variant_pool or self._current_tile is None:
            self.selection = None
            return
        variant = self._variant_pool[self._variant_index]
        center = grid.tile_to_world_center(self._current_tile)
        self.selection = GhostSelection(variant, self._current_tile, center)

    # --- Queries ---
    @property
    def current_tile(self) -> Optional[TileCoord]:
        return self._current_tile

    def current_variant(self) -> Optional[str]:
        return self.selection.variant_key if self.selection else None

    def current_center(self) -> Optional[Vec2f]:
        return self.selection.world_center if self.selection else None

    def set_player(self, player) -> None:
        self.player = player

    def set_validator(self, fn: Optional[Callable[[GhostSelection], bool]]) -> None:
        self._validator = fn

    # --- Validation ---
    def is_valid(self) -> bool:
        if not self.selection or self._current_tile is None:
            return False
        variant_key = self.selection.variant_key
        center = self.selection.world_center

        if self.placed.get_entry_for_world_pos(center):
            return False

        variant = data.get_variant(variant_key)
        if variant is None:
            return False
        local_poly = variant.collision_polygon
        if not local_poly:
            return False
        scale = float(variant.scale)
        offsets = variant.collision_offsets
        poly_world = transform_local64_to_world(local_poly, center, scale, offsets)

        if self.collision and hasattr(self.collision, "overlaps_obstacles_poly"):
            if self.collision.overlaps_obstacles_poly(poly_world):
                return False

        player = self.player
        if player is not None:
            px, py = player.world_pos
            model = getattr(player, "model", None)
            w = getattr(model, "w", PLAYER_SIZE)
            h = getattr(model, "h", PLAYER_SIZE)
            fx = px + (float(w) - float(PLAYER_FEET_W)) / 2.0
            fy = py + (float(h) - float(PLAYER_FEET_H))
            feet_aabb = (fx, fy, fx + float(PLAYER_FEET_W), fy + float(PLAYER_FEET_H))
            fence_aabb = aabb_from_points(poly_world)
            if aabb_overlap(feet_aabb, fence_aabb):
                return False

        if self._validator and not self._validator(self.selection):
            return False

        return True

    def selection_is_valid(self) -> bool:
        return self.is_valid()

    # --- Rendering ---
    def draw(self, surface, camera) -> None:
        if not self.selection:
            return
        variant_key = self.selection.variant_key
        center = self.selection.world_center
        variant = data.get_variant(variant_key)
        if variant is None:
            return
        surf = self.placed.get_surface(variant)
        if surf is None:
            return
        scale = float(variant.scale)
        world_w = surf.get_width() * scale
        world_h = surf.get_height() * scale
        tl_world = (center[0] - world_w / 2.0, center[1] - world_h / 2.0)
        sx, sy = camera.world_to_screen(tl_world)
        cs = float(getattr(camera, "scale", 1.0))
        draw_w = int(round(world_w * cs))
        draw_h = int(round(world_h * cs))
        if draw_w <= 0 or draw_h <= 0:
            return
        if abs(scale * cs - 1.0) < 1e-6:
            draw_surf = surf
        else:
            draw_surf = pygame.transform.scale(surf, (draw_w, draw_h))
        ghost_surf = draw_surf.copy()
        tint = pygame.Surface(ghost_surf.get_size(), pygame.SRCALPHA)
        tint.fill(self.tint_valid if self.is_valid() else self.tint_invalid)
        ghost_surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(ghost_surf, (int(round(sx)), int(round(sy))))
