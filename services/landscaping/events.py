from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

TileCoords = Tuple[int, int]


@dataclass(frozen=True, slots=True)
class TileHarvestEvent:
    """Details about a tile harvested via LandscapingSystem."""

    tile_coords: TileCoords
    previous_tile_code: int
    was_moss: bool
    player: object


__all__ = ["TileHarvestEvent"]
