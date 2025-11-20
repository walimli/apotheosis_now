from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from systems.player.components.soul.safe_zone import (
    SafeZoneRegistry,
    resolve_safe_zone_radius,
)

from .dawn_growth import DawnGrowthController
from .placeables_animator import PlaceableAnimationController
from .placeables_asset_loader import PlaceablesAssetLoader
from .placeables_json_reader import PlaceableRecord
from .protection import ProtectionRegistry

TileCoord = Tuple[int, int]
ChunkKey = Tuple[int, int]


@dataclass
class PlaceableInstance:
    item_id: str
    dataset_name: Optional[str]
    record: PlaceableRecord
    tile: TileCoord
    chunk_key: ChunkKey
    object_entry: Dict[str, object]
    bundle_key: Optional[str]
    sprite_id: str
    collider_id: Optional[int] = None
    durability: Optional[int] = None


@dataclass
class GrowthTracker:
    dataset_name: str
    record_key: str


class PlaceableInstanceRegistry:
    """Manage placed instances, growth tracking, and related bookkeeping."""

    def __init__(
        self,
        *,
        asset_loader: PlaceablesAssetLoader,
        chunk_objects: Dict[ChunkKey, List[Dict[str, object]]],
        chunk_size: int,
        tile_size: int,
        protection: ProtectionRegistry,
        safe_zones: SafeZoneRegistry,
        dawn_growth: DawnGrowthController,
        object_type: str = "placeable",
        world_renderer: Optional[object] = None,
        collision: Optional[object] = None,
    ) -> None:
        self._asset_loader = asset_loader
        self._chunk_objects = chunk_objects
        self._chunk_size = int(chunk_size)
        self._tile_size = int(tile_size)
        self._protection = protection
        self._safe_zones = safe_zones
        self._dawn_growth = dawn_growth
        self._object_type = object_type
        self._collision = collision

        object_sprites = getattr(world_renderer, "object_sprites", {}) if world_renderer else {}
        scale_cache = getattr(world_renderer, "_object_scale_cache", None) if world_renderer else None

        self._animations = PlaceableAnimationController(
            asset_loader=self._asset_loader,
            object_sprites=object_sprites,
            sprite_id_factory=self._sprite_id,
            scale_cache=scale_cache,
        )

        self._instances: Dict[TileCoord, PlaceableInstance] = {}
        self._growth_targets: Dict[TileCoord, GrowthTracker] = {}
        self._next_collider_id = -1
        self._targeting_adapter = None
        self._targeting_recompute: Optional[Callable[[], None]] = None

    def set_targeting_hooks(self, adapter, recompute_callback: Optional[Callable[[], None]]) -> None:
        self._targeting_adapter = adapter
        self._targeting_recompute = recompute_callback

    # --- Public API -------------------------------------------------
    @property
    def instances(self) -> Dict[TileCoord, PlaceableInstance]:
        return dict(self._instances)

    def advance_animations(self, dt: float) -> None:
        self._animations.advance(dt)

    def is_tile_occupied(self, tile: TileCoord) -> bool:
        return tile in self._instances

    def register_instance(
        self,
        *,
        item_id: str,
        dataset_name: Optional[str],
        record: PlaceableRecord,
        tile: TileCoord,
        bundle_key: Optional[str],
    ) -> PlaceableInstance:
        chunk_key = self._chunk_key(tile)
        local_x = tile[0] - chunk_key[0] * self._chunk_size
        local_y = tile[1] - chunk_key[1] * self._chunk_size
        sprite_id = self._animations.register_instance(tile, dataset_name, record)
        offset_x, offset_y = record.collision_offsets
        aabb_world = self._record_aabb_world(record, tile)
        entry: Dict[str, object] = {
            "id": sprite_id,
            "type": self._object_type,
            "tile": tile,
            "x": local_x,
            "y": local_y,
            "z": record.z_index,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "scale": float(record.scale),
            "ysort_anchor_fraction": record.ysort_anchor_fraction,
            "ysort_offset_px": record.ysort_offset_px,
            "aabb": aabb_world,
        }
        bucket = self._chunk_objects.setdefault(chunk_key, [])
        bucket.append(entry)

        durability = None
        if record.durability_max is not None:
            try:
                durability = max(0, int(record.durability_max))
            except Exception:
                durability = None
        if durability is not None:
            entry["durability"] = durability

        instance = PlaceableInstance(
            item_id=item_id,
            dataset_name=dataset_name,
            record=record,
            tile=tile,
            chunk_key=chunk_key,
            object_entry=entry,
            bundle_key=bundle_key,
            sprite_id=sprite_id,
            durability=durability,
        )
        if self._collision is not None:
            collider_id = self._next_collider_id
            self._next_collider_id -= 1
            self._collision.append_chunk_collider(
                chunk_key[0],
                chunk_key[1],
                {
                    "instance_id": collider_id,
                    "category": self._object_type,
                    "aabb": aabb_world,
                },
            )
            instance.collider_id = collider_id

        self._instances[tile] = instance
        self._sync_safe_zone(tile, dataset_name, record)
        self._update_growth_tracker(tile, dataset_name, record)
        if record.protection_radius:
            self._protection.add_zone(tile, record.protection_radius)
        self._notify_targeting("on_placeable_added", instance)
        return instance

    def remove_instance(self, tile: TileCoord) -> Optional[PlaceableInstance]:
        instance = self._instances.pop(tile, None)
        if instance is None:
            return None

        bucket = self._chunk_objects.get(instance.chunk_key)
        if bucket:
            try:
                bucket.remove(instance.object_entry)
            except ValueError:
                pass
            if not bucket:
                self._chunk_objects.pop(instance.chunk_key, None)

        self._animations.unregister(tile)
        self._growth_targets.pop(tile, None)
        if self._safe_zones is not None:
            self._safe_zones.remove_zone(tile)
        self._protection.remove_zone(tile)

        if instance.collider_id is not None and self._collision is not None:
            cx, cy = instance.chunk_key
            self._collision.remove_instance(cx, cy, instance.collider_id)

        self._notify_targeting("on_placeable_removed", instance)
        return instance

    def advance_growth(self) -> None:
        updates: List[Tuple[TileCoord, PlaceableRecord]] = []
        for tile, tracker in list(self._growth_targets.items()):
            step = self._dawn_growth.next_step(tracker.dataset_name, tracker.record_key)
            if step is None:
                self._growth_targets.pop(tile, None)
                continue
            updates.append((tile, step.next))
            if not step.next.dawn_growth:
                self._growth_targets.pop(tile, None)
            else:
                self._growth_targets[tile] = GrowthTracker(
                    dataset_name=tracker.dataset_name,
                    record_key=step.next.key,
                )
        for tile, new_record in updates:
            instance = self._instances.get(tile)
            if instance is None:
                continue
            instance.record = new_record
            sprite_id = self._animations.update_instance(tile, instance.dataset_name, new_record)
            instance.object_entry["id"] = sprite_id
            instance.object_entry["z"] = new_record.z_index
            ox, oy = new_record.collision_offsets
            instance.object_entry["offset_x"] = ox
            instance.object_entry["offset_y"] = oy
            instance.object_entry["scale"] = float(new_record.scale)
            instance.object_entry["ysort_anchor_fraction"] = new_record.ysort_anchor_fraction
            instance.object_entry["ysort_offset_px"] = new_record.ysort_offset_px
            instance.bundle_key = new_record.image_path
            instance.sprite_id = sprite_id

            new_aabb = self._record_aabb_world(new_record, tile)
            instance.object_entry["aabb"] = new_aabb
            if instance.collider_id and self._collision is not None:
                cx, cy = instance.chunk_key
                self._collision.remove_instance(cx, cy, instance.collider_id)
                self._collision.append_chunk_collider(
                    cx,
                    cy,
                    {
                        "instance_id": instance.collider_id,
                        "category": self._object_type,
                        "aabb": new_aabb,
                    },
                )

            self._sync_safe_zone(tile, instance.dataset_name, new_record)
            self._notify_targeting("on_placeable_moved", instance)

    # --- Internal helpers -------------------------------------------
    def _sync_safe_zone(
        self,
        tile: TileCoord,
        dataset_name: Optional[str],
        record: PlaceableRecord,
    ) -> None:
        if self._safe_zones is None:
            return
        self._safe_zones.remove_zone(tile)
        radius = resolve_safe_zone_radius(dataset_name, record.safe_zone_radius)
        if radius > 0:
            self._safe_zones.add_zone(tile, radius)

    def _update_growth_tracker(
        self,
        tile: TileCoord,
        dataset_name: Optional[str],
        record: PlaceableRecord,
    ) -> None:
        if record.dawn_growth and dataset_name:
            self._growth_targets[tile] = GrowthTracker(
                dataset_name=dataset_name,
                record_key=record.key,
            )
        elif tile in self._growth_targets:
            self._growth_targets.pop(tile, None)

    def _chunk_key(self, tile: TileCoord) -> ChunkKey:
        return tile[0] // self._chunk_size, tile[1] // self._chunk_size

    def _record_aabb_world(self, record: PlaceableRecord, tile: TileCoord) -> Tuple[float, float, float, float]:
        center_x = (tile[0] + 0.5) * self._tile_size
        center_y = (tile[1] + 0.5) * self._tile_size
        aabb = record.collision_aabb
        offsets = record.collision_offsets
        scale = float(record.scale)
        half_tile = self._tile_size / 2.0

        local_min_x = aabb.offset_x
        local_min_y = aabb.offset_y
        local_max_x = local_min_x + aabb.width
        local_max_y = local_min_y + aabb.height

        min_x = center_x + ((local_min_x - half_tile + offsets[0]) * scale)
        min_y = center_y + ((local_min_y - half_tile + offsets[1]) * scale)
        max_x = center_x + ((local_max_x - half_tile + offsets[0]) * scale)
        max_y = center_y + ((local_max_y - half_tile + offsets[1]) * scale)

        return (min_x, min_y, max_x, max_y)

    def _sprite_id(self, dataset_name: Optional[str], record_key: str) -> str:
        if dataset_name:
            return f"{dataset_name}:{record_key}"
        return record_key

    def _notify_targeting(self, method: str, instance: Optional[PlaceableInstance]) -> None:
        if (
            instance is None
            or getattr(instance, "collider_id", None) is None
            or self._targeting_adapter is None
        ):
            return
        handler = getattr(self._targeting_adapter, method, None)
        if handler is None:
            return
        handler(instance)
        if self._targeting_recompute is not None:
            self._targeting_recompute()


__all__ = [
    "PlaceableInstanceRegistry",
    "PlaceableInstance",
    "GrowthTracker",
]
