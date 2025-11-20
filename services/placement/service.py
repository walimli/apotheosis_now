"""Placement service wiring inventory, placer, and ghost rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Optional, Sequence, Tuple

import pygame

from constants import TILE_CODE_VOID
from ecs_core.components import Health, Position, Soul
from ecs_core.components.entity_classes import Object, Plant
from ecs_core.worlds.world import World
from services.display.display_system import DisplayService
from services.inventory.cursor import InventoryCursor
from services.inventory.inventory import Inventory
from services.monster_factory import MonsterFactoryService

from .blueprints import PlacementBlueprint, build_default_blueprints
from .ghost import PlacementGhost
from .pills import PillRegistry, PillSpec
from .placer import PlacementPlacer, PlacementResult
from .selection import PlacementInventoryListener, PlacementSelectionState

TileCoord = Tuple[int, int]


class PlacementService:
    """Coordinates placement selection, preview, and placement attempts."""

    FENCE_ITEM_IDS: Sequence[str] = ()

    def __init__(
        self,
        *,
        inventory: Inventory,
        cursor: InventoryCursor,
        world: World,
        player_entity: int,
        monster_factory: MonsterFactoryService,
        display: DisplayService,
        tile_size: int,
        tile_lookup: Callable[[int, int], Optional[int]],
        project_root: Optional[Path] = None,
        placement_radius: int = 2,
        void_tile_codes: Sequence[int] = (TILE_CODE_VOID,),
        pill_registry: Optional[PillRegistry] = None,
    ) -> None:
        self._inventory = inventory
        self._cursor = cursor
        self._world = world
        self._player_entity = int(player_entity)
        self._monster_factory = monster_factory
        self._display = display
        self._tile_size = int(tile_size)
        self._tile_lookup = tile_lookup
        self._void_tiles = tuple(int(code) for code in void_tile_codes)
        self._crafting_active = False
        self._last_screen_pos: Optional[Tuple[int, int]] = None
        self._active_camera = None

        root = Path(project_root or Path(__file__).resolve().parents[2])
        self._blueprints: Dict[str, PlacementBlueprint] = build_default_blueprints(root)
        self._pill_registry = pill_registry or PillRegistry(project_root=root)

        self._ghost = PlacementGhost()
        self._placer = PlacementPlacer(
            inventory=inventory,
            cursor=cursor,
            ghost=self._ghost,
            tile_size=self._tile_size,
            placement_radius=placement_radius,
            void_tile_query=self._is_void_tile,
            occupancy_query=self._is_tile_occupied,
            player_tile_query=self._player_tile,
        )

        self._selection_listener = PlacementInventoryListener(
            inventory,
            blueprints=self._blueprints,
            pill_registry=self._pill_registry,
            fence_items=set(self.FENCE_ITEM_IDS),
        )
        self._selection_listener.subscribe(self._handle_selection_state)
        self._selection_listener.attach()
        self._selection_state: PlacementSelectionState = self._selection_listener.state

    # --- Input handlers -------------------------------------------------
    def handle_cursor_move(self, pos: Optional[Tuple[int, int]], camera) -> None:
        self._last_screen_pos = pos
        base_pos = self._map_screen_to_base(pos)
        state = self._selection_state
        camera_ref = self._active_camera or camera
        if not state.blueprint or not self._placer.is_active():
            self._placer.handle_cursor_move(None, camera_ref)
            return
        self._placer.handle_cursor_move(base_pos, camera_ref)

    def handle_use_inventory(self, camera) -> bool:
        if self._crafting_active:
            return False
        state = self._selection_state
        if state.handled_by_fence:
            return False
        if state.is_pill:
            return self._attempt_pill_use(camera)
        if not state.blueprint:
            return False
        return self._attempt_entity_placement()

    def handle_variant_cycle(self) -> bool:
        # Reserved for future variant-aware placeables (e.g., fences).
        return False

    def use_active_pill(self) -> bool:
        return self._consume_pill_selection()

    # --- Rendering ------------------------------------------------------
    def render(self, surface: pygame.Surface, camera) -> None:
        self._active_camera = camera
        self._placer.draw(surface, camera)

    # --- Crafting integration ------------------------------------------
    def set_crafting_active(self, active: bool) -> None:
        self._crafting_active = bool(active)
        if active:
            self._placer.activate(None, None)

    # --- Internal helpers ----------------------------------------------
    def _handle_selection_state(self, state: PlacementSelectionState) -> None:
        self._selection_state = state
        if (
            state.blueprint
            and not self._crafting_active
            and not self._cursor.carrying()
            and state.qty > 0
        ):
            self._placer.activate(state.item_id, state.blueprint)
        else:
            self._placer.activate(None, None)

    def _attempt_entity_placement(self) -> bool:
        result: PlacementResult = self._placer.try_place()
        print(
            f"[Placement] try_place -> success={result.success}, "
            f"tile={result.tile}, blueprint={getattr(result.blueprint, 'entity_id', None)}"
        )
        if not result.success or not result.tile or not result.blueprint:
            print("[Placement] Placement failed before spawn")
            return False
        entity_id = result.blueprint.entity_id
        if not entity_id:
            print("[Placement] Placement missing entity_id")
            return False
        self._monster_factory.spawn_entity_at_tile(entity_id, result.tile)
        print(f"[Placement] Spawn requested for '{entity_id}' at {result.tile}")
        return True

    def _attempt_pill_use(self, camera) -> bool:
        if not self._selection_state.is_pill:
            return False
        return self._consume_pill_selection(camera=camera)

    def _consume_pill_selection(self, camera=None) -> bool:
        state = self._selection_state
        if not state.is_pill or not state.item_id:
            return False
        if camera is not None and not self._cursor_over_player(camera):
            return False
        spec = self._pill_registry.get(state.item_id)
        if spec is None:
            return False
        if not self._apply_pill(spec):
            return False
        removed = self._inventory.remove_from_selected(1)
        if removed != 1:
            self._inventory.add(state.item_id, 1)
            return False
        return True

    def _apply_pill(self, spec: PillSpec) -> bool:
        if spec.effect == "health":
            health = self._world.get(self._player_entity, Health)
            if not health:
                return False
            healed = health.heal(spec.magnitude)
            return healed > 0
        if spec.effect == "soul":
            soul = self._world.get(self._player_entity, Soul)
            if not soul:
                return False
            before = int(getattr(soul, "current_soul", 0))
            soul.current_soul = min(soul.max_soul, before + spec.magnitude)
            return soul.current_soul > before
        return False

    def _cursor_over_player(self, camera) -> bool:
        base_pos = self._map_screen_to_base(self._last_screen_pos)
        tile = self._base_to_tile(base_pos, camera)
        player_tile = self._player_tile()
        return tile is not None and player_tile is not None and tile == player_tile

    def _base_to_tile(
        self, base_pos: Optional[Tuple[int, int]], camera
    ) -> Optional[TileCoord]:
        if base_pos is None:
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
        world_x = rect.left + base_pos[0] / scale
        world_y = rect.top + base_pos[1] / scale
        return (int(world_x // self._tile_size), int(world_y // self._tile_size))

    def _player_tile(self) -> Optional[TileCoord]:
        position = self._world.get(self._player_entity, Position)
        if position is None:
            return None
        tile_x = int(float(position.x) // self._tile_size)
        tile_y = int(float(position.y) // self._tile_size)
        return (tile_x, tile_y)

    def _is_void_tile(self, tile: TileCoord) -> bool:
        value = self._tile_lookup(tile[0], tile[1])
        if value is None:
            return True
        return int(value) in self._void_tiles

    def _is_tile_occupied(self, tile: TileCoord) -> bool:
        for entity, pos, _obj in self._world.view(Position, Object):
            if entity == self._player_entity:
                continue
            if self._tile_from_position(pos) == tile:
                return True
        for entity, pos, _plant in self._world.view(Position, Plant):
            if entity == self._player_entity:
                continue
            if self._tile_from_position(pos) == tile:
                return True
        return False

    def _tile_from_position(self, pos: Position) -> TileCoord:
        return (
            int(float(pos.x) // self._tile_size),
            int(float(pos.y) // self._tile_size),
        )

    def _map_screen_to_base(
        self, screen_pos: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        if screen_pos is None:
            return None
        if self._display is None:
            return screen_pos
        try:
            scale, off_x, off_y = self._display.get_present_params()
        except Exception:
            return screen_pos
        denom = max(1, int(scale))
        bx = int((screen_pos[0] - off_x) // denom)
        by = int((screen_pos[1] - off_y) // denom)
        return (bx, by)


__all__ = ["PlacementService"]
