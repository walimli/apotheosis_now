"""Placement placer logic wired to inventory and input events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import pygame

from services.inventory.inventory import Inventory
from services.inventory.cursor import InventoryCursor

from .blueprints import PlacementBlueprint
from .ghost import PlacementGhost

TileCoord = Tuple[int, int]
Vec2 = Tuple[float, float]


@dataclass
class PlacementResult:
    success: bool
    tile: Optional[TileCoord] = None
    blueprint: Optional[PlacementBlueprint] = None


class PlacementPlacer:
    """Handle tile validation, ghost updates, and placement attempts."""

    def __init__(
        self,
        *,
        inventory: Inventory,
        cursor: InventoryCursor,
        ghost: PlacementGhost,
        tile_size: int,
        placement_radius: int,
        void_tile_query: Callable[[TileCoord], bool],
        occupancy_query: Callable[[TileCoord], bool],
        player_tile_query: Callable[[], Optional[TileCoord]],
    ) -> None:
        self.inventory = inventory
        self.cursor = cursor
        self.ghost = ghost
        self.tile_size = int(tile_size)
        self.placement_radius = max(0, int(placement_radius))
        self._void_tile_query = void_tile_query
        self._occupancy_query = occupancy_query
        self._player_tile_query = player_tile_query

        self._active_blueprint: Optional[PlacementBlueprint] = None
        self._active_item_id: Optional[str] = None
        self._candidate_tile: Optional[TileCoord] = None
        self._last_valid: bool = False

    def activate(self, item_id: Optional[str], blueprint: Optional[PlacementBlueprint]) -> None:
        if item_id == self._active_item_id and blueprint == self._active_blueprint:
            return
        self._active_item_id = item_id
        self._active_blueprint = blueprint
        self._candidate_tile = None
        self.ghost.deactivate()

    def is_active(self) -> bool:
        return (
            self._active_blueprint is not None
            and self._active_item_id is not None
            and not self.cursor.carrying()
            and self.inventory.get_selected_item_id() == self._active_item_id
        )

    def handle_cursor_move(
        self,
        screen_pos: Optional[Tuple[int, int]],
        camera,
        *,
        dt: float = 0.0,
    ) -> None:
        if not self.is_active() or screen_pos is None:
            self._candidate_tile = None
            self.ghost.deactivate()
            return
        tile = self._tile_from_mouse(screen_pos, camera)
        if tile is None:
            self._candidate_tile = None
            self.ghost.deactivate()
            return
        self._candidate_tile = tile
        valid = self._validate_tile(tile)
        self._last_valid = valid
        if not self._active_blueprint:
            self.ghost.deactivate()
            return
        center = self._tile_center(tile)
        if not self.ghost.is_active:
            self.ghost.activate(self._active_blueprint, center)
        else:
            self.ghost.move_to(center)
        self.ghost.set_valid(valid)
        self.ghost.update(dt)

    def draw(self, surface: pygame.Surface, camera) -> None:
        if self.is_active():
            self.ghost.draw(surface, camera)

    def current_tile(self) -> Optional[TileCoord]:
        return self._candidate_tile

    def can_place_current_tile(self) -> bool:
        return self._candidate_tile is not None and self._last_valid

    def try_place(self, consume: Optional[Callable[[], bool]] = None) -> PlacementResult:
        if not self.is_active() or not self._active_blueprint:
            print(
                f"[Placer] try_place aborted: active={self.is_active()}, "
                f"blueprint={getattr(self._active_blueprint, 'entity_id', None)}"
            )
            return PlacementResult(False)
        tile = self._candidate_tile
        if tile is None or not self._validate_tile(tile):
            print(f"[Placer] try_place invalid tile: {tile}")
            return PlacementResult(False)
        # Capture blueprint/item before inventory mutations (selection events can clear them).
        blueprint = self._active_blueprint
        item_id = self._active_item_id
        consumer = consume or self._consume_from_slot
        if not consumer():
            print("[Placer] try_place failed to consume inventory")
            return PlacementResult(False)
        print(
            f"[Placer] try_place success for item {item_id} "
            f"-> tile={tile}, blueprint={getattr(blueprint, 'entity_id', None)}"
        )
        return PlacementResult(True, tile=tile, blueprint=blueprint)

    def _consume_from_slot(self) -> bool:
        slot = self.inventory.get_selected_slot()
        if slot.is_empty() or slot.item_id != self._active_item_id:
            return False
        removed = self.inventory.remove_from_selected(1)
        return removed == 1

    def _validate_tile(self, tile: TileCoord) -> bool:
        blueprint = self._active_blueprint
        if blueprint is None:
            return False
        player_tile = self._player_tile_query()
        if player_tile is None:
            return False
        if blueprint.requires_player_tile and tile != player_tile:
            return False
        if not self._within_radius(player_tile, tile, blueprint.placement_radius or self.placement_radius):
            return False
        if self._void_tile_query(tile):
            return False
        if not blueprint.ignore_occupancy and self._occupancy_query(tile):
            return False
        return True

    def _tile_from_mouse(self, mouse_pos: Tuple[int, int], camera) -> Optional[TileCoord]:
        if camera is None:
            return None
        scale = float(getattr(camera, "scale", 1.0))
        if hasattr(camera, "get_camera_scale"):
            scale = float(camera.get_camera_scale())
        if scale <= 0:
            scale = 1.0
        rect = getattr(camera, "rect", None)
        if rect is None and hasattr(camera, "get_camera_rect"):
            rect = camera.get_camera_rect()
        if rect is None:
            rect = pygame.Rect(0, 0, 0, 0)
        world_x = rect.left + mouse_pos[0] / scale
        world_y = rect.top + mouse_pos[1] / scale
        tile_x = int(world_x // self.tile_size)
        tile_y = int(world_y // self.tile_size)
        return (tile_x, tile_y)

    def _within_radius(self, origin: TileCoord, target: TileCoord, radius: int) -> bool:
        ox, oy = origin
        tx, ty = target
        return max(abs(ox - tx), abs(oy - ty)) <= radius

    def _tile_center(self, tile: TileCoord) -> Vec2:
        cx = tile[0] * self.tile_size + self.tile_size / 2.0
        cy = tile[1] * self.tile_size + self.tile_size / 2.0
        return (cx, cy)


__all__ = ["PlacementPlacer", "PlacementResult"]
