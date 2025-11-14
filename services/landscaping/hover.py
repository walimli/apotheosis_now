from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from services.landscaping.geometry import player_tile_indices, screen_to_tile
from services.landscaping.inventory_listener import LandscapingSelectionState

TileCoords = Tuple[int, int]


@dataclass
class HoverState:
    harvest_target: Optional[TileCoords] = None
    placement_target: Optional[TileCoords] = None


def compute_hover(
    *,
    player_position: Optional[Tuple[float, float]],
    camera,
    tile_size: int,
    updater,
    mouse_pos: Optional[Tuple[int, int]],
    selection_state: LandscapingSelectionState,
    harvestable_tiles: Tuple[int, ...],
    void_tile_code: int,
    reach: int = 1,
) -> HoverState:
    """Determine current hover targets for harvesting or placement."""
    state = HoverState()
    if mouse_pos is None or player_position is None:
        return state

    tile_coords = screen_to_tile(camera, tile_size, mouse_pos)
    if not _is_tile_reachable(player_position, tile_size, tile_coords, reach):
        return state

    tile_value = updater.get_tile_value(*tile_coords)
    if tile_value is None:
        return state

    if selection_state.harvest_enabled and tile_value in harvestable_tiles:
        state.harvest_target = tile_coords
    elif (
        selection_state.placement_tile_code is not None
        and tile_value == void_tile_code
        and selection_state.qty > 0
    ):
        state.placement_target = tile_coords
    return state


def _is_tile_reachable(
    player_position: Tuple[float, float],
    tile_size: int,
    tile_coords: TileCoords,
    reach: int,
) -> bool:
    player_tile = player_tile_indices(player_position, tile_size)
    dx = tile_coords[0] - player_tile[0]
    dy = tile_coords[1] - player_tile[1]
    return abs(dx) <= reach and abs(dy) <= reach
