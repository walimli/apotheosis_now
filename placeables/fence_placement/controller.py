"""Input/controller layer for the fence placement system."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import pygame

from constants import PLAYER_SIZE, TILE_SIZE

from . import adjacency, data, grid, ghost
from .geometry import aabb_from_points, transform_local64_to_world

Vec2f = Tuple[float, float]
TileCoord = Tuple[int, int]


_FACING_TO_STEP = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class FencePlacementController:
    """Manage fence placement activation, ghost state, and input."""

    def __init__(
        self,
        world,
        placed_manager,
        *,
        tile_size: int = TILE_SIZE,
        placement_radius: int = 2,
        collider_category: str = "fence",
    ) -> None:
        self.world = world
        self.placed = placed_manager
        self.collision = getattr(world, "collision", None)
        self.ghost = ghost.FenceGhost(world, self.collision, placed_manager)
        self.active: bool = False
        self.item_id: Optional[str] = None
        self._player = None
        self.tile_size = int(tile_size)
        self.placement_radius = max(0, int(placement_radius))
        self._cursor_tile: Optional[TileCoord] = None
        self._collider_category = str(collider_category)
        self.ghost.set_validator(self._selection_is_valid)

    # --- Lifecycle ---
    def begin(self, player, item_id: str) -> bool:
        variants = _variants_for_item(item_id)
        if not variants:
            return False
        self.active = True
        self.item_id = item_id
        self._player = player
        self.ghost.set_player(player)
        self._cursor_tile = None
        self._sync_to_current_tile()
        return True

    def cancel(self) -> None:
        self.active = False
        self.item_id = None
        self._player = None
        self.ghost.set_player(None)
        self.ghost.deactivate()
        self._cursor_tile = None

    def update(self) -> None:
        if not self.active:
            return
        self._sync_to_current_tile()

    def draw_ghost(self, surface, camera) -> None:
        self.ghost.draw(surface, camera)

    # --- Input ---
    def handle_event(self, event) -> Optional[bool]:
        if not self.active:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._commit_selection()
            if event.button == 3:
                self.ghost.cycle_variant(1)
                return True
        return None

    def commit_selection(self) -> bool:
        if not self.active:
            return False
        return self._commit_selection()

    def cycle_variant(self, step: int = 1) -> bool:
        if not self.active:
            return False
        self.ghost.cycle_variant(step)
        return True

    def set_cursor_tile(self, tile: Optional[TileCoord]) -> None:
        self._cursor_tile = tile
        self._sync_to_current_tile()

    # --- Helpers ---
    def _desired_tile(self) -> Optional[TileCoord]:
        if self._cursor_tile is not None:
            return self._cursor_tile
        return self._player_facing_tile()

    def _player_facing_tile(self) -> TileCoord:
        if not self._player:
            return (0, 0)
        center = _player_center(self._player)
        base_tile = grid.world_to_tile(center)
        facing = getattr(self._player, "facing", "down")
        dx, dy = _FACING_TO_STEP.get(facing, (0, 1))
        return (base_tile[0] + dx, base_tile[1] + dy)

    def _sync_to_current_tile(self) -> None:
        if not self.active:
            return
        tile = self._desired_tile()
        if tile is None:
            self.ghost.update_variant_pool([])
            return
        pool, preferred = self._variant_options_for_tile(tile)
        if not self.ghost.active or self.ghost.current_tile != tile:
            self.ghost.activate(tile, pool, preferred=preferred)
        else:
            self.ghost.update_variant_pool(pool, preferred=preferred)

    def _variant_options_for_tile(
        self, tile: TileCoord
    ) -> Tuple[Iterable[str], Optional[str]]:
        if not self.item_id:
            return (), None
        candidate_keys = data.variants_for_item(self.item_id)
        required = adjacency.collect_adjacent_edges(tile, self.placed)
        pool = adjacency.build_variant_pool(required, candidate_keys)
        if not pool:
            pool = list(candidate_keys)
        preferred = None
        if not required:
            facing = getattr(self._player, "facing", "down")
            desired = "wfvcon" if facing in ("left", "right") else "wfhcon"
            preferred = _first_with_variant_id(pool, desired) or _first_with_variant_id(
                candidate_keys, desired
            )
        return pool, preferred

    def _commit_selection(self) -> bool:
        if not self.ghost.selection or not self.ghost.is_valid():
            return False
        player = self._player
        if not player or not self.item_id:
            return False
        inv = getattr(player, "inventory", None)
        if inv is None:
            return False
        slot = inv.get_selected_slot()
        if slot.is_empty() or slot.item_id != self.item_id or slot.qty <= 0:
            return False
        if not self._selection_is_valid(self.ghost.selection):
            return False

        variant_key = self.ghost.selection.variant_key
        center = self.ghost.selection.world_center
        variant = data.get_variant(variant_key)
        if variant is None:
            return False
        local_poly = variant.collision_polygon
        if not local_poly:
            return False
        scale = float(variant.scale)
        offsets = variant.collision_offsets
        poly_world = transform_local64_to_world(local_poly, center, scale, offsets)
        aabb = aabb_from_points(poly_world)

        cx, cy, instance_id = self.placed.add_fence(center, variant, poly_world, aabb)

        if self.collision and hasattr(self.collision, "append_chunk_collider"):
            collider = {
                "chunk": (cx, cy),
                "instance_id": int(instance_id),
                "asset_key": variant.asset_key,
                "category": self._collider_category,
                "poly": tuple(poly_world),
                "aabb": aabb,
            }
            self.collision.append_chunk_collider(cx, cy, collider)

        taken = inv.remove_from_selected(1)
        if taken != 1:
            if self.collision and hasattr(self.collision, "remove_instance"):
                self.collision.remove_instance(cx, cy, instance_id)
            self.placed.remove_instance(cx, cy, instance_id)
            return False

        self.cancel()
        return True

    def _selection_is_valid(self, selection: ghost.GhostSelection) -> bool:
        if selection is None:
            return False
        return self._within_radius(selection.tile)

    def _within_radius(self, tile: TileCoord) -> bool:
        if not self._player or tile is None:
            return False
        px, py = getattr(self._player, "world_pos", (0.0, 0.0))
        tx = int(tile[0])
        ty = int(tile[1])
        tile_size = self.tile_size if self.tile_size > 0 else TILE_SIZE
        player_tile = (int(px // tile_size), int(py // tile_size))
        return max(abs(player_tile[0] - tx), abs(player_tile[1] - ty)) <= self.placement_radius


def _variants_for_item(item_id: str) -> Tuple[str, ...]:
    return data.variants_for_item(item_id)


def _player_center(player) -> Vec2f:
    px, py = player.world_pos
    model = getattr(player, "model", None)
    w = getattr(model, "w", PLAYER_SIZE)
    h = getattr(model, "h", PLAYER_SIZE)
    return (px + float(w) / 2.0, py + float(h) / 2.0)


def _first_with_variant_id(keys: Sequence[str], variant_id: str) -> Optional[str]:
    for key in keys:
        variant = data.get_variant(key)
        if variant and variant.variant_id == variant_id:
            return key
    return None
