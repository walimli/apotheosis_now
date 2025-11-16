from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import pygame

from ecs_core.components import Position
from services.landscaping.landscape_updater import LandscapeUpdater
from services.landscaping.events import TileHarvestEvent
from services.landscaping.moss_harvest import SPORE_COIN_ITEM_ID
from services.landscaping.inventory_listener import (
    LandscapingInventoryListener,
    LandscapingSelectionState,
)
from services.landscaping.hover import HoverState, compute_hover
from services.landscaping.overlay import HoverOverlay

TileCoords = Tuple[int, int]


class LandscapingSystem:
    """Coordinates landscaping interactions for the play state."""

    HARVESTABLE_TILES = (1, 2, 3, 14, 24, 34)
    PICK_ITEM_ID = "pick_wooden_medallion"
    SPORE_ITEM_ID = SPORE_COIN_ITEM_ID
    VOID_TILE_CODE = 0

    # Mapping between inventory item ids and placement tile codes
    PLACEMENT_ITEM_TO_TILE = {
        "clay_coin": 1,
        "redrock_coin": 2,
        "stone_coin": 3,
    }

    # Mapping between tile codes and harvest reward item ids
    BIOME_COIN_BY_TILE = {
        1: "clay_coin",
        2: "redrock_coin",
        3: "stone_coin",
    }

    def __init__(self, play_state, updater: LandscapeUpdater) -> None:
        self._play_state = play_state
        self._updater = updater
        self._player = play_state.player
        self._display = getattr(play_state, "display", None)
        self._camera = self._display
        self._world = getattr(play_state, "ecs_world", None)
        self._player_entity = getattr(play_state, "player_entity", None)
        self._inventory = getattr(self._player, "inventory", None)
        if self._inventory is None:
            raise ValueError(
                "Player inventory is required for landscaping interactions"
            )
        world_renderer = getattr(play_state, "world_renderer", None)
        if world_renderer is None:
            raise ValueError(
                "World renderer is required for landscaping interactions"
            )
        self._tile_size = getattr(world_renderer, "tile_size", 64)
        tile_sheet = getattr(play_state, "tile_sheet", None)
        self._hover_overlay = (
            HoverOverlay(tile_size=self._tile_size, tile_sheet=tile_sheet)
            if tile_sheet is not None
            else None
        )
        self._hover_state = HoverState()
        self._cursor_base_pos: Optional[Tuple[int, int]] = None
        self._harvest_listeners: list[Callable[[TileHarvestEvent], None]] = []
        self._selection_listener = LandscapingInventoryListener(
            self._inventory,
            harvest_item_id=self.PICK_ITEM_ID,
            placement_items=self.PLACEMENT_ITEM_TO_TILE,
        )
        self._selection_state: LandscapingSelectionState = (
            self._selection_listener.state
        )
        self._selection_listener.subscribe(self._handle_selection_update)
        self._selection_listener.attach()

    def handle_cursor_move(
        self, pos: Optional[Tuple[int, int]], camera=None
    ) -> None:
        if camera is not None:
            self._camera = camera
        elif self._camera is None:
            self._camera = self._display
        self._cursor_base_pos = self._map_screen_to_base(pos)
        self._update_hover()

    def handle_use_inventory(self) -> None:
        combat = getattr(self._play_state, "combat_system", None)
        if combat is not None:
            handler = getattr(combat, "try_placeable_strike", None)
            if callable(handler) and handler():
                return
        self._handle_primary_click()

    def update(self, dt: float) -> None:
        _ = dt  # Landscaping currently has no per-frame simulation

    def render(self, surface: pygame.Surface) -> None:
        if self._hover_overlay is None:
            return
        camera = self._camera or self._display
        if camera is None:
            return
        self._hover_overlay.draw(surface, camera, self._hover_state)

    def add_harvest_listener(
        self, listener: Callable[[TileHarvestEvent], None]
    ) -> None:
        if listener not in self._harvest_listeners:
            self._harvest_listeners.append(listener)

    def remove_harvest_listener(
        self, listener: Callable[[TileHarvestEvent], None]
    ) -> None:
        if listener in self._harvest_listeners:
            self._harvest_listeners.remove(listener)

    def _handle_primary_click(self) -> None:
        self._update_hover()
        performed = False
        if self._is_pick_selected():
            target = self._hover_state.harvest_target
            if target is not None:
                self._perform_harvest(target)
                performed = True
        if not performed:
            placement = self._selected_placement()
            target = self._hover_state.placement_target
            if placement is not None and target is not None:
                self._perform_placement(target)
                performed = True
        if performed:
            self._update_hover()

    def _handle_selection_update(
        self, state: LandscapingSelectionState
    ) -> None:
        self._selection_state = state
        self._update_hover()

    def _is_pick_selected(self) -> bool:
        return self._selection_state.harvest_enabled

    def _selected_placement(self) -> Optional[Tuple[str, int]]:
        state = self._selection_state
        if state.placement_tile_code is None:
            return None
        item_id = state.item_id
        if item_id is None or state.qty <= 0:
            return None
        return item_id, state.placement_tile_code

    def wants_primary_action(self) -> bool:
        state = self._selection_state
        if state.harvest_enabled:
            return True
        return (
            state.placement_tile_code is not None
            and state.item_id is not None
            and state.qty > 0
        )

    def _perform_harvest(self, tile_coords: TileCoords) -> None:
        tile_value = self._updater.get_tile_value(*tile_coords)
        if tile_value is None or tile_value not in self.HARVESTABLE_TILES:
            return

        val = int(tile_value)
        is_moss_tile = val >= 10
        base_code = (val // 10) if is_moss_tile else val
        biome_item_id = self.BIOME_COIN_BY_TILE.get(base_code)
        if biome_item_id is None:
            return

        rewards: List[Tuple[str, int]] = [(biome_item_id, 1)]
        if is_moss_tile:
            rewards.append((self.SPORE_ITEM_ID, 1))

        if hasattr(self._inventory, "get_free_space"):
            for reward_id, qty in rewards:
                if self._inventory.get_free_space(reward_id) < qty:
                    return

        mutation = self._updater.set_tile_value(
            tile_coords[0], tile_coords[1], self.VOID_TILE_CODE
        )
        if mutation is None:
            return

        self._trigger_attack_animation()

        awarded: List[Tuple[str, int]] = []
        for reward_id, qty in rewards:
            remainder = self._inventory.add(reward_id, qty)
            if remainder:
                self._updater.set_tile_value(tile_coords[0], tile_coords[1], tile_value)
                self._rollback_inventory_awards(awarded)
                return
            awarded.append((reward_id, qty))

        self._notify_tile_harvest(tile_coords, tile_value, is_moss_tile)

    def _rollback_inventory_awards(self, awards: List[Tuple[str, int]]) -> None:
        if not awards:
            return
        for reward_id, qty in reversed(awards):
            remaining = qty
            for slot_index, slot in enumerate(getattr(self._inventory, "slots", [])):
                if getattr(slot, "item_id", None) != reward_id:
                    continue
                slot_qty = getattr(slot, "qty", 0)
                if slot_qty <= 0:
                    continue
                removed = self._inventory.remove_from_slot(
                    slot_index, min(slot_qty, remaining)
                )
                remaining -= removed
                if remaining <= 0:
                    break
            if remaining > 0:
                raise RuntimeError(
                    f"Failed to rollback inventory award for {reward_id}"
                )

    def _perform_placement(self, tile_coords: TileCoords) -> None:
        selection = self._selected_placement()
        if selection is None:
            return
        item_id, tile_code = selection
        tile_value = self._updater.get_tile_value(*tile_coords)
        if tile_value is None or tile_value != self.VOID_TILE_CODE:
            return

        removed = self._inventory.remove_from_selected(1)
        if removed != 1:
            return

        mutation = self._updater.set_tile_value(
            tile_coords[0], tile_coords[1], tile_code
        )
        if mutation is None:
            self._inventory.add(item_id, removed)
            return

        # Selection handled by unified targeting; no hover refresh

        controller = getattr(self._player, "controller", None)
        if controller is not None:
            controller.handle_inventory_use(pick_equipped=False)

    def _player_world_center(self) -> Optional[Tuple[float, float]]:
        if self._world is None or self._player_entity is None:
            return None
        position = self._world.get(self._player_entity, Position)
        if position is None:
            return None
        base_x = position.render_x if position.render_x is not None else float(position.x)
        base_y = position.render_y if position.render_y is not None else float(position.y)
        return base_x, base_y

    def _update_hover(self) -> None:
        camera = self._camera or self._display
        player_pos = self._player_world_center()
        if camera is None or player_pos is None:
            self._hover_state = HoverState()
            return
        self._hover_state = compute_hover(
            player_position=player_pos,
            camera=camera,
            tile_size=self._tile_size,
            updater=self._updater,
            mouse_pos=self._cursor_base_pos,
            selection_state=self._selection_state,
            harvestable_tiles=self.HARVESTABLE_TILES,
            void_tile_code=self.VOID_TILE_CODE,
        )

    def _map_screen_to_base(
        self, pos: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        if pos is None:
            return None
        display = self._display
        if display is None:
            return (int(pos[0]), int(pos[1]))
        try:
            scale, off_x, off_y = display.get_present_params()
        except Exception:
            return (int(pos[0]), int(pos[1]))
        denom = max(1, int(scale))
        bx = int((pos[0] - off_x) // denom)
        by = int((pos[1] - off_y) // denom)
        return (bx, by)

    def _trigger_attack_animation(self) -> None:
        controller = getattr(self._player, "controller", None)
        if controller is None:
            return
        controller.handle_inventory_use(pick_equipped=True)

    def _notify_tile_harvest(
        self,
        tile_coords: TileCoords,
        previous_tile_code: int,
        was_moss: bool,
    ) -> None:
        if not self._harvest_listeners:
            return
        event = TileHarvestEvent(
            tile_coords=tile_coords,
            previous_tile_code=previous_tile_code,
            was_moss=was_moss,
            player=self._player,
        )
        for listener in list(self._harvest_listeners):
            try:
                listener(event)
            except Exception:
                continue


__all__ = ["LandscapingSystem"]
