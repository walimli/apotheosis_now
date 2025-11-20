"""Management layer for fence placement, storage, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union

import pygame

from .fence_placement import data as fence_data
from .fence_placement import grid
from .fence_placement.controller import FencePlacementController
from .fence_placement.data import FenceVariant
from .placeables_asset_loader import PlaceablesAssetLoader
from .placeables_json_reader import PlaceableRecord

Vec2f = Tuple[float, float]
TileCoord = Tuple[int, int]
ChunkKey = Tuple[int, int]


@dataclass
class FenceInstance:
    """Book-keeping for a placed fence instance."""

    tile: TileCoord
    chunk_key: ChunkKey
    instance_id: int
    variant_key: str
    variant_id: str
    item_id: str
    connecting_edges: Tuple[str, ...]
    sprite_id: str
    object_entry: Dict[str, object]
    record: PlaceableRecord
    durability: Optional[int] = None


class FenceManager:
    """Encapsulate fence placement logic and placed fence records."""

    OBJECT_TYPE = "fence"

    def __init__(
        self,
        *,
        world,
        asset_loader: PlaceablesAssetLoader,
        chunk_objects: Dict[ChunkKey, List[Dict[str, object]]],
        chunk_size: int,
        tile_size: int,
        object_sprites: Dict[str, pygame.Surface],
        placement_radius: int = 2,
        collider_category: Optional[str] = None,
    ) -> None:
        self._world = world
        self._asset_loader = asset_loader
        self._chunk_objects = chunk_objects
        self._chunk_size = int(chunk_size)
        self._tile_size = int(tile_size)
        self._object_sprites = object_sprites
        self._placement_radius = max(0, int(placement_radius))
        self._collision = getattr(world, "collision", None)
        self._collider_category = collider_category or self.OBJECT_TYPE

        self._controller = FencePlacementController(
            world,
            self,
            tile_size=self._tile_size,
            placement_radius=self._placement_radius,
            collider_category=self._collider_category,
        )

        self._instances: Dict[TileCoord, FenceInstance] = {}
        self._id_lookup: Dict[int, TileCoord] = {}
        self._next_instance_id = 1
        self._surface_cache: Dict[str, pygame.Surface] = {}

        self._player = None
        self._active_item_id: Optional[str] = None

    # --- Activation -------------------------------------------------
    @property
    def collider_category(self) -> str:
        return self._collider_category

    def instances_by_id(self) -> Dict[int, FenceInstance]:
        mapping: Dict[int, FenceInstance] = {}
        for instance_id, tile in self._id_lookup.items():
            instance = self._instances.get(tile)
            if instance is not None:
                mapping[int(instance_id)] = instance
        return mapping

    def get_instance_by_id(self, instance_id: int) -> Optional[FenceInstance]:
        tile = self._id_lookup.get(int(instance_id))
        if tile is None:
            return None
        return self._instances.get(tile)

    def activate_item(self, player, item_id: Optional[str]) -> bool:
        """Activate placement for the provided item_id if it is a fence."""
        if not item_id:
            self.deactivate()
            return False
        variants = fence_data.variants_for_item(item_id)
        if not variants:
            self.deactivate()
            return False

        if self.is_active() and self._active_item_id == item_id and self._player is player:
            return True

        self.deactivate()
        success = self._controller.begin(player, item_id)
        if success:
            self._player = player
            self._active_item_id = item_id
        return success

    def deactivate(self) -> None:
        if self._controller.active:
            self._controller.cancel()
        self._active_item_id = None
        self._player = None

    def is_active(self) -> bool:
        return self._controller.active

    # --- Event handling ---------------------------------------------
    def handle_mouse_motion(self, pos: Tuple[int, int], camera) -> None:
        _ = (pos, camera)

    def handle_mouse_button(self, event, camera) -> bool:
        if event.button == 1:
            return self.handle_use_inventory()
        if event.button == 3:
            return self.handle_variant_cycle()
        return False

    def set_cursor_tile(self, tile: Optional[TileCoord]) -> None:
        self._controller.set_cursor_tile(tile)

    def handle_use_inventory(self) -> bool:
        handled = bool(self._controller.commit_selection())
        if handled and not self._controller.active and self._player and self._active_item_id:
            # Attempt to resume placement if inventory still holds the item.
            self.activate_item(self._player, self._active_item_id)
        return handled

    def handle_variant_cycle(self) -> bool:
        handled = bool(self._controller.cycle_variant(1))
        return handled

    def update(self, dt: float) -> None:
        if not self.is_active():
            return
        self._controller.update()

    def render(self, surface: pygame.Surface, camera) -> None:
        if not self.is_active():
            return
        self._controller.draw_ghost(surface, camera)

    # --- Controller callbacks ---------------------------------------
    def get_surface(self, variant: Union[FenceVariant, str]) -> Optional[pygame.Surface]:
        fence_variant = self._resolve_variant(variant)
        if not fence_variant:
            return None
        return self._ensure_surface(fence_variant)

    def get_tile_entry(self, tile_x: int, tile_y: int) -> Optional[Dict[str, object]]:
        tile = (int(tile_x), int(tile_y))
        instance = self._instances.get(tile)
        return self._serialize_instance(instance) if instance else None

    def get_entry_for_world_pos(self, world_pos: Vec2f) -> Optional[Dict[str, object]]:
        tile = grid.world_to_tile(world_pos)
        return self.get_tile_entry(*tile)

    def add_fence(
        self,
        center: Vec2f,
        variant: FenceVariant,
        poly_world: Iterable[Tuple[float, float]],
        aabb: Tuple[float, float, float, float],
    ) -> Tuple[int, int, int]:
        _ = (poly_world, aabb)
        tile = grid.world_to_tile(center)
        chunk_key = self._chunk_key(tile)
        local_x = tile[0] - chunk_key[0] * self._chunk_size
        local_y = tile[1] - chunk_key[1] * self._chunk_size

        sprite_id = self._sprite_id(variant)
        surface = self._ensure_render_surface(variant, sprite_id)
        offset_x, offset_y = self._sprite_offsets(surface)

        record = variant.record
        durability = None
        if record.durability_max is not None:
            try:
                durability = max(0, int(record.durability_max))
            except Exception:
                durability = None

        object_entry: Dict[str, object] = {
            "id": sprite_id,
            "type": self.OBJECT_TYPE,
            "tile": tile,
            "x": local_x,
            "y": local_y,
            "z": record.z_index,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }
        if durability is not None:
            object_entry["durability"] = durability
        bucket = self._chunk_objects.setdefault(chunk_key, [])
        bucket.append(object_entry)

        instance_id = self._next_instance_id
        self._next_instance_id += 1

        instance = FenceInstance(
            tile=tile,
            chunk_key=chunk_key,
            instance_id=instance_id,
            variant_key=variant.key,
            variant_id=variant.variant_id,
            item_id=variant.item_id,
            connecting_edges=tuple(variant.connecting_edges),
            sprite_id=sprite_id,
            object_entry=object_entry,
            record=record,
            durability=durability,
        )
        self._instances[tile] = instance
        self._id_lookup[instance_id] = tile

        return chunk_key[0], chunk_key[1], instance_id

    def remove_instance(self, chunk_x: int, chunk_y: int, instance_id: int) -> Optional[FenceInstance]:
        instance_id = int(instance_id)
        tile = self._id_lookup.pop(instance_id, None)
        if tile is None:
            return None
        instance = self._instances.pop(tile, None)
        if instance is None:
            return None

        bucket = self._chunk_objects.get((chunk_x, chunk_y))
        if not bucket:
            bucket = None
        try:
            if bucket is not None:
                bucket.remove(instance.object_entry)
        except ValueError:
            pass
        if bucket is not None and not bucket:
            self._chunk_objects.pop((chunk_x, chunk_y), None)

        if self._collision and hasattr(self._collision, "remove_instance"):
            try:
                self._collision.remove_instance(chunk_x, chunk_y, instance_id)
            except Exception:
                pass

        return instance

    def remove_instance_by_id(self, instance_id: int) -> Optional[FenceInstance]:
        instance = self.get_instance_by_id(instance_id)
        if instance is None:
            return None
        chunk_x, chunk_y = instance.chunk_key
        return self.remove_instance(chunk_x, chunk_y, instance_id)

    # --- Helpers ----------------------------------------------------
    def _chunk_key(self, tile: TileCoord) -> ChunkKey:
        return tile[0] // self._chunk_size, tile[1] // self._chunk_size

    def _sprite_id(self, variant: FenceVariant) -> str:
        return variant.asset_key

    def _sprite_offsets(self, surface: pygame.Surface) -> Tuple[float, float]:
        width = float(surface.get_width())
        height = float(surface.get_height())
        half_tile = self._tile_size / 2.0
        return (half_tile - width / 2.0, half_tile - height / 2.0)

    def _ensure_surface(self, variant: FenceVariant) -> pygame.Surface:
        cached = self._surface_cache.get(variant.key)
        if cached is not None:
            return cached
        bundle = self._asset_loader.load_bundle(variant.record)
        surface = bundle.frame(0)
        self._surface_cache[variant.key] = surface
        return surface

    def _ensure_render_surface(self, variant: FenceVariant, sprite_id: str) -> pygame.Surface:
        base_surface = self._ensure_surface(variant)
        scale = float(variant.scale)
        if abs(scale - 1.0) < 1e-6:
            render_surface = base_surface
        else:
            width = max(1, int(round(base_surface.get_width() * scale)))
            height = max(1, int(round(base_surface.get_height() * scale)))
            render_surface = pygame.transform.smoothscale(base_surface, (width, height))
        self._object_sprites[sprite_id] = render_surface
        return render_surface

    def _resolve_variant(self, variant: Union[FenceVariant, str]) -> Optional[FenceVariant]:
        if isinstance(variant, FenceVariant):
            return variant
        return fence_data.get_variant(variant)

    @staticmethod
    def _serialize_instance(instance: Optional[FenceInstance]) -> Optional[Dict[str, object]]:
        if instance is None:
            return None
        return {
            "variant_key": instance.variant_key,
            "variant_id": instance.variant_id,
            "item_id": instance.item_id,
            "connecting_edges": tuple(instance.connecting_edges),
        }


__all__ = ["FenceManager"]
