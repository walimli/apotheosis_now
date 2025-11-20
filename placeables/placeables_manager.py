from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import pygame

from systems.player.components.inventory_package.inventory import Inventory
from systems.player.components.inventory_package.cursor import InventoryCursor

from .dawn_growth import DawnGrowthController
from .placeables_asset_loader import PlaceablesAssetLoader
from .placeables_json_reader import PlaceablesJsonReader
from .placeables_placer import PlaceablesPlacer
from .placeables_ghost import PlaceableGhost
from .pills import PillRegistry
from .protection import ProtectionRegistry
from systems.player.components.soul.safe_zone import SafeZoneRegistry
from .fence_manager import FenceManager, FenceInstance
from .placeable_registry import PlaceableInstanceRegistry, PlaceableInstance

TileCoord = Tuple[int, int]
ChunkKey = Tuple[int, int]


class PlaceablesManager:
    """Coordinate placeable selection, placement, and lifecycle updates."""

    OBJECT_TYPE = "placeable"

    def __init__(
        self,
        *,
        inventory: Inventory,
        cursor: InventoryCursor,
        player,
        reader: PlaceablesJsonReader,
        asset_loader: PlaceablesAssetLoader,
        ghost: PlaceableGhost,
        pill_registry: PillRegistry,
        dawn_growth: DawnGrowthController,
        protection: ProtectionRegistry,
        safe_zones: SafeZoneRegistry,
        chunk_objects: Dict[ChunkKey, List[Dict[str, object]]],
        chunk_size: int,
        tile_size: int,
        tile_value_lookup: Callable[[int, int], int],
        void_tile_codes: Tuple[int, ...],
        player_tile_query: Callable[[], TileCoord],
        # removed external crafting_active_query polling; internal flag is used instead
        spore_planter: Optional[Callable[[TileCoord], bool]] = None,
        world_renderer: Optional[object] = None,
        placement_radius: int = 2,
        fence_manager: Optional[FenceManager] = None,
        collision=None,
    ) -> None:
        self.inventory = inventory
        self.cursor = cursor
        self._player = player
        self._reader = reader
        self._asset_loader = asset_loader
        self._ghost = ghost
        self._pill_registry = pill_registry
        self._dawn_growth = dawn_growth
        self._protection = protection
        self._safe_zones = safe_zones
        self._chunk_objects = chunk_objects
        self._chunk_size = int(chunk_size)
        self._tile_size = int(tile_size)
        self._tile_value_lookup = tile_value_lookup
        self._void_codes = set(void_tile_codes)
        self._player_tile_query = player_tile_query
        self._crafting_active: bool = False
        self._spore_planter = spore_planter
        self._world_renderer = world_renderer
        self._placement_radius = max(0, int(placement_radius))

        self._placer = PlaceablesPlacer(
            inventory=inventory,
            cursor=cursor,
            reader=self._reader.load_dataset,
            asset_loader=asset_loader,
            ghost=ghost,
            tile_size=self._tile_size,
            occupancy_query=self._is_tile_occupied,
            void_tile_query=self._is_void_tile,
            player_tile_query=self._player_tile_query,
            crafting_active_query=self._is_crafting_active,
            placement_radius=self._placement_radius,
        )

        self._last_mouse_pos: Optional[Tuple[int, int]] = None
        self._registry = PlaceableInstanceRegistry(
            asset_loader=self._asset_loader,
            chunk_objects=self._chunk_objects,
            chunk_size=self._chunk_size,
            tile_size=self._tile_size,
            protection=self._protection,
            safe_zones=self._safe_zones,
            dawn_growth=self._dawn_growth,
            object_type=self.OBJECT_TYPE,
            world_renderer=world_renderer,
            collision=collision,
        )
        self._active_source: str = "slot"
        self._fences = fence_manager

    # --- Inventory binding ---
    def set_active_item(self, item_id: Optional[str], *, source: str = "slot") -> None:
        if not item_id:
            if self._fences:
                self._fences.deactivate()
            self._deactivate()
            return
        if self._fences and self._fences.activate_item(self._player, item_id):
            self._active_source = source
            self._placer.activate_item(None)
            return
        if self._fences:
            self._fences.deactivate()
        self._active_source = source
        self._placer.activate_item(item_id)

    def _deactivate(self) -> None:
        self._placer.activate_item(None)
        self._active_source = "slot"

    def _ensure_active_state(self) -> bool:
        if self._fences and self._fences.is_active():
            return False
        if not self._placer.is_active():
            return False
        if self._is_crafting_active():
            self._deactivate()
            return False
        current_id = self._placer.current_item_id()
        if self._active_source == "cursor":
            if not self.cursor.carrying() or self.cursor.item_id != current_id:
                self._deactivate()
                return False
        else:
            if self.cursor.carrying() and self.cursor.item_id != current_id:
                self._deactivate()
                return False
        return True

    # --- Event handling ---
    def handle_mouse_motion(self, pos: Tuple[int, int], camera) -> None:
        self.handle_cursor_move(pos, camera)

    def handle_cursor_move(self, pos: Tuple[int, int] | None, camera) -> None:
        if pos is None:
            self._last_mouse_pos = None
            if self._fences and self._fences.is_active():
                self._fences.set_cursor_tile(None)
            if hasattr(self._placer, "ghost"):
                self._placer.ghost.deactivate()
            return
        self._last_mouse_pos = (int(pos[0]), int(pos[1]))
        if self._fences and self._fences.is_active():
            tile = self._screen_to_tile(self._last_mouse_pos, camera)
            self._fences.set_cursor_tile(tile)
            return
        if not self._ensure_active_state():
            return
        self._placer.update(0.0, self._last_mouse_pos, camera)

    def update(self, dt: float, camera) -> None:
        if self._fences and self._fences.is_active():
            self._fences.update(dt)
        elif self._last_mouse_pos is not None and self._ensure_active_state():
            self._placer.update(dt, self._last_mouse_pos, camera)
        self._registry.advance_animations(dt)

    def render(self, surface: pygame.Surface, camera) -> None:
        if self._fences and self._fences.is_active():
            self._fences.render(surface, camera)
            return
        self._placer.draw_ghost(surface, camera)

    def handle_mouse_button(self, event: pygame.event.Event, camera) -> bool:
        if event.button == 1:
            return self.handle_use_inventory(camera)
        if event.button == 3:
            return self.handle_variant_cycle()
        return False

    def handle_use_inventory(self, camera) -> bool:
        if self._fences and self._fences.is_active():
            handled = self._fences.handle_use_inventory()
            if handled and self._last_mouse_pos is not None:
                tile = self._screen_to_tile(self._last_mouse_pos, camera)
                self._fences.set_cursor_tile(tile)
                self._play_use_animation(pick_equipped=False)
            return handled
        if not self._ensure_active_state():
            return False
        pos = self._last_mouse_pos
        if pos is None:
            return False

        item_id = self._placer.current_item_id()
        if not item_id:
            return False

        if self._pill_registry.is_pill(item_id):
            success = self._attempt_pill_use(item_id, pos, camera)
            if success:
                self._play_use_animation(pick_equipped=False)
            return success

        if item_id == "spore_coin":
            success = self._attempt_spore_placement(pos, camera)
            if success:
                self._play_use_animation(pick_equipped=False)
            return success

        result = self._placer.try_place()
        if not result.success or result.tile is None or result.record is None:
            return False
        self._registry.register_instance(
            item_id=item_id,
            dataset_name=result.dataset_name,
            record=result.record,
            tile=result.tile,
            bundle_key=result.bundle_key,
        )
        self._play_use_animation(pick_equipped=False)
        return True

    def handle_variant_cycle(self) -> bool:
        if self._fences and self._fences.is_active():
            return self._fences.handle_variant_cycle()
        return False

    def use_active_pill(self) -> bool:
        selected = self.inventory.get_selected_item_id()
        if not selected or not self._pill_registry.is_pill(selected):
            return False
        applied = self._pill_registry.apply(selected, player=self._player)
        if not applied:
            return False
        removed = self.inventory.remove_from_selected(1)
        if removed != 1:
            self.inventory.add(selected, 1)
            return False
        self._play_use_animation(pick_equipped=False)
        return True

    # --- Internal helpers ---
    def _attempt_pill_use(self, item_id: str, pos: Tuple[int, int], camera) -> bool:
        if not self._click_hits_player(pos, camera):
            return False
        applied = self._pill_registry.apply(item_id, player=self._player)
        if not applied:
            return False
        removed = self.inventory.remove_from_selected(1)
        if removed != 1:
            self.inventory.add(item_id, 1)
            return False
        return True

    def _attempt_spore_placement(self, pos: Tuple[int, int], camera) -> bool:
        if self._spore_planter is None:
            return False
        tile = self._placer.current_tile()
        if tile is None or not self._placer.can_place_current_tile():
            return False
        removed = self.inventory.remove_from_selected(1)
        if removed != 1:
            return False
        planted = self._spore_planter(tile)
        if not planted:
            # refund on failure
            self.inventory.add("spore_coin", 1)
            return False
        return True

    def handle_time_event(self, event) -> None:
        event_type = getattr(event, "event_type", None)
        if hasattr(event_type, "name") and event_type.name == "DAWN_STARTED":
            self._registry.advance_growth()

    def remove_instance(self, tile: TileCoord) -> Optional[PlaceableInstance]:
        return self._registry.remove_instance(tile)

    def _play_use_animation(self, pick_equipped: bool) -> None:
        controller = getattr(self._player, "controller", None)
        if controller is not None:
            controller.handle_inventory_use(pick_equipped=pick_equipped)

    # --- Tile queries ---
    def _is_tile_occupied(self, tile: TileCoord) -> bool:
        return self._registry.is_tile_occupied(tile)

    def _is_void_tile(self, tile: TileCoord) -> bool:
        value = self._tile_value_lookup(tile[0], tile[1])
        return value in self._void_codes

    def _screen_to_tile(self, pos: Tuple[int, int], camera) -> Optional[TileCoord]:
        if camera is None or pos is None:
            return None
        scale = float(getattr(camera, "scale", 1.0))
        cam_rect = getattr(camera, "rect", pygame.Rect(0, 0, 0, 0))
        world_x = cam_rect.left + pos[0] / scale
        world_y = cam_rect.top + pos[1] / scale
        return (int(world_x // self._tile_size), int(world_y // self._tile_size))

    # --- Misc helpers ---
    def _click_hits_player(self, pos: Tuple[int, int], camera) -> bool:
        if camera is None:
            return False
        model = getattr(self._player, "model", None)
        if model is None:
            return False

        px, py, pw, ph = model.rect
        sx, sy = camera.world_to_screen((px, py))
        scale = float(getattr(camera, "scale", 1.0))
        sw = pw * scale
        sh = ph * scale
        screen_rect = pygame.Rect(
            int(round(sx)), int(round(sy)), int(round(sw)), int(round(sh))
        )
        return screen_rect.collidepoint(pos)

    # Properties for external queries
    @property
    def instances(self) -> Dict[TileCoord, PlaceableInstance]:
        return self._registry.instances

    @property
    def _instances(self) -> Dict[TileCoord, PlaceableInstance]:
        # Expose underlying mapping for legacy consumers (e.g., targeting helpers).
        return self._registry._instances  # type: ignore[attr-defined]

    @property
    def fences(self) -> Optional[FenceManager]:
        return self._fences

    @property
    def safe_zones(self) -> SafeZoneRegistry:
        return self._safe_zones

    def fence_instances_by_collider_id(self) -> Dict[int, FenceInstance]:
        if self._fences is None:
            return {}
        return self._fences.instances_by_id()

    def attach_targeting_adapter(self, adapter, recompute_callback) -> None:
        if adapter is None or recompute_callback is None:
            return
        if hasattr(self._registry, "set_targeting_hooks"):
            self._registry.set_targeting_hooks(adapter, recompute_callback)

    # --- Crafting state integration ---
    def set_crafting_active(self, active: bool) -> None:
        self._crafting_active = bool(active)
        if self._crafting_active:
            self._deactivate()

    def _is_crafting_active(self) -> bool:
        return self._crafting_active


__all__ = ["PlaceablesManager"]
