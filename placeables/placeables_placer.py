from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Tuple

import pygame

from systems.player.components.inventory_package.inventory import Inventory
from systems.player.components.inventory_package.cursor import InventoryCursor

from .placeables_json_reader import PlaceableDataset, PlaceableRecord
from .placeables_asset_loader import PlaceablesAssetLoader, PlaceableSpriteBundle

STANDARD_DATASET_LOOKUP: Dict[str, Tuple[str, str]] = {
    "glow_spore_coin": ("glow_tree", "glow_seedling"),
    "health_pill": ("pills", "health_pill"),
    "spore_coin": ("spore_seedling", "seedling"),
    "crystal_coin": ("crystals", "crystal_seedling"),
    "skull_candle_coin": ("skull_candle", "skull_candle"),
    "skull_shrine_coin": ("skull_shrine", "skull_shrine"),
}

PILL_ITEMS: Tuple[str, ...] = ("health_pill",)

from .placeables_ghost import PlaceableGhost

Vec2f = Tuple[float, float]
TileCoord = Tuple[int, int]


def _tile_center(tile_x: int, tile_y: int, tile_size: int) -> Vec2f:
    return (tile_x * tile_size + tile_size / 2.0, tile_y * tile_size + tile_size / 2.0)


def _tile_top_left(tile_x: int, tile_y: int, tile_size: int) -> Vec2f:
    return (tile_x * tile_size, tile_y * tile_size)


@dataclass
class PlacementResult:
    success: bool
    tile: Optional[TileCoord] = None
    record: Optional[PlaceableRecord] = None
    bundle_key: Optional[str] = None
    dataset_name: Optional[str] = None


class PlaceablesPlacer:
    """Handle user interactions for placing placeable items in the world."""

    def __init__(
        self,
        *,
        inventory: Inventory,
        cursor: InventoryCursor,
        reader: Callable[[str], PlaceableDataset],
        asset_loader: PlaceablesAssetLoader,
        ghost: PlaceableGhost,
        tile_size: int,
        occupancy_query: Callable[[TileCoord], bool],
        void_tile_query: Callable[[TileCoord], bool],
        player_tile_query: Callable[[], TileCoord],
        crafting_active_query: Callable[[], bool],
        placement_radius: int = 2,
    ) -> None:
        self.inventory = inventory
        self.cursor = cursor
        self._load_dataset = reader
        self.asset_loader = asset_loader
        self.ghost = ghost
        self.tile_size = tile_size
        self.occupancy_query = occupancy_query
        self.void_tile_query = void_tile_query
        self.player_tile_query = player_tile_query
        self.crafting_active_query = crafting_active_query
        self.placement_radius = max(0, int(placement_radius))

        self._active_item: Optional[str] = None
        self._active_record: Optional[PlaceableRecord] = None
        self._active_bundle_key: Optional[str] = None
        self._active_dataset_name: Optional[str] = None
        self._candidate_tile: Optional[TileCoord] = None
        self._cached_bundle: Optional[PlaceableSpriteBundle] = None
        self._ghost_record_key: Optional[str] = None
        self._ghost_bundle_key: Optional[str] = None
        self._ghost_world_pos: Vec2f = (0.0, 0.0)
        self._require_player_tile: bool = False
        self._ignore_occupancy: bool = False

    # --- Activation ---
    def activate_item(self, item_id: Optional[str]) -> None:
        if item_id == self._active_item:
            return
        self._active_item = item_id
        self._active_record = None
        self._active_bundle_key = None
        self._active_dataset_name = None
        self._candidate_tile = None
        self.ghost.deactivate()
        self._cached_bundle = None
        self._ghost_record_key = None
        self._ghost_bundle_key = None
        self._require_player_tile = False
        self._ignore_occupancy = False

        if not item_id:
            return

        dataset_name, record_key = self._resolve_dataset_for_item(item_id)
        if not dataset_name or not record_key:
            return
        dataset = self._load_dataset(dataset_name)
        try:
            record = dataset.get(record_key)
        except KeyError:
            return

        self._active_record = record
        self._active_dataset_name = dataset_name
        self._active_bundle_key = record.image_path
        self._require_player_tile = item_id in PILL_ITEMS
        self._ignore_occupancy = self._require_player_tile

    def deactivate(self) -> None:
        self.activate_item(None)

    def is_active(self) -> bool:
        return self._active_record is not None

    # --- Frame updates ---
    def update(self, dt: float, mouse_pos: Tuple[int, int], camera) -> None:
        if not self.is_active():
            return
        if self.crafting_active_query():
            self.deactivate()
            return
        if self.cursor.carrying():
            self.deactivate()
            return

        tile = self._tile_from_mouse(mouse_pos, camera)
        self._candidate_tile = tile
        bundle = self._load_active_bundle()
        if not bundle or not self._active_record:
            self.ghost.deactivate()
            self._ghost_record_key = None
            self._ghost_bundle_key = None
            return

        valid = False
        top_left = self._sprite_top_left_for_tile(tile, bundle) if tile else (0.0, 0.0)
        if tile:
            valid = self._validate_tile(tile)

        bundle_key = self._active_bundle_key
        record_key = self._active_record.key

        if (
            not self.ghost.is_active
            or record_key != self._ghost_record_key
            or bundle_key != self._ghost_bundle_key
        ):
            self.ghost.activate(self._active_record, bundle, top_left)
            self._ghost_world_pos = top_left
            self._ghost_record_key = record_key
            self._ghost_bundle_key = bundle_key
        else:
            if top_left != self._ghost_world_pos:
                self.ghost.move_to(top_left)
                self._ghost_world_pos = top_left

        self.ghost.set_valid(valid)
        self.ghost.update(dt)

    def draw_ghost(self, surface: pygame.Surface, camera) -> None:
        self.ghost.draw(surface, camera)

    # --- Placement ---
    def try_place(self, consume: Optional[Callable[[], bool]] = None) -> PlacementResult:
        if (
            not self.is_active()
            or self._candidate_tile is None
            or not self._active_record
        ):
            return PlacementResult(False)
        tile = self._candidate_tile
        if not self._validate_tile(tile):
            return PlacementResult(False)

        record = self._active_record
        bundle_key = self._active_bundle_key
        dataset_name = self._active_dataset_name
        consumer = consume or self._consume_from_slot
        if not consumer():
            return PlacementResult(False)
        return PlacementResult(
            True,
            tile=tile,
            record=record,
            bundle_key=bundle_key,
            dataset_name=dataset_name,
        )

    def _consume_from_slot(self) -> bool:
        slot = self.inventory.get_selected_slot()
        if slot is None or slot.is_empty() or slot.item_id != self._active_item:
            return False
        removed = self.inventory.remove_from_selected(1)
        return removed == 1

    def current_item_id(self) -> Optional[str]:
        return self._active_item

    def current_tile(self) -> Optional[TileCoord]:
        return self._candidate_tile

    def can_place_current_tile(self) -> bool:
        if self._candidate_tile is None:
            return False
        return self._validate_tile(self._candidate_tile)

    # --- Helpers ---
    def _resolve_dataset_for_item(
        self, item_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        if item_id in STANDARD_DATASET_LOOKUP:
            return STANDARD_DATASET_LOOKUP[item_id]
        return None, None

    def _tile_from_mouse(self, mouse_pos: Tuple[int, int], camera) -> Optional[TileCoord]:
        cam_scale = float(getattr(camera, "scale", 1.0))
        cam_rect = getattr(camera, "rect", pygame.Rect(0, 0, 0, 0))
        screen_x, screen_y = mouse_pos
        world_x = cam_rect.left + screen_x / cam_scale
        world_y = cam_rect.top + screen_y / cam_scale
        tile_x = int(world_x // self.tile_size)
        tile_y = int(world_y // self.tile_size)
        return (tile_x, tile_y)

    def _validate_tile(self, tile: TileCoord) -> bool:
        player_tile = self.player_tile_query()
        if not self._within_radius(player_tile, tile, self.placement_radius):
            return False
        if self.void_tile_query(tile):
            return False
        if self._require_player_tile and tile != player_tile:
            return False
        if not self._ignore_occupancy and self.occupancy_query(tile):
            return False
        return True

    def _within_radius(self, origin: TileCoord, target: TileCoord, radius: int) -> bool:
        ox, oy = origin
        tx, ty = target
        return max(abs(ox - tx), abs(oy - ty)) <= radius

    def _load_active_bundle(self):
        if not self._active_record:
            return None
        if not self._active_record:
            return None
        if self._cached_bundle is not None:
            return self._cached_bundle
        try:
            self._cached_bundle = self.asset_loader.load_bundle(self._active_record)
        except FileNotFoundError:
            self._cached_bundle = None
        return self._cached_bundle

    def _sprite_top_left_for_tile(
        self, tile: Optional[TileCoord], bundle: PlaceableSpriteBundle
    ):
        if tile is None:
            return (0.0, 0.0)
        center = _tile_center(tile[0], tile[1], self.tile_size)
        scale = float(self._active_record.scale if self._active_record else 1.0)
        width = bundle.image.get_width() * scale
        height = bundle.image.get_height() * scale
        return (center[0] - width / 2.0, center[1] - height / 2.0)


__all__ = ["PlaceablesPlacer", "PlacementResult"]
