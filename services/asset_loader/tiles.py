"""Tilesheet loading and slicing utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pygame

TILESHEET_FILENAME = "tilesheet.png"
TILESHEET_COLUMNS = 10
TILESHEET_ROWS = 5


@dataclass(frozen=True)
class TileSheet:
    """Container for sliced tile surfaces."""

    tiles: List[List[pygame.Surface]]
    tile_size: int

    def get(self, row: int, col: int) -> pygame.Surface:
        """Return the tile surface at (row, col)."""
        return self.tiles[row][col]

    @property
    def rows(self) -> int:
        return len(self.tiles)

    @property
    def cols(self) -> int:
        return len(self.tiles[0]) if self.tiles else 0


def load_tilesheet(
    *,
    tile_size: Optional[int] = None,
    asset_root: Optional[Path] = None,
) -> TileSheet:
    """Load the shared tilesheet, slice it into tiles, and scale to `tile_size`."""
    base_path = asset_root or Path(__file__).resolve().parents[2] / "assets" / "tiles"
    sheet_path = base_path / TILESHEET_FILENAME
    if not sheet_path.exists():
        raise FileNotFoundError(f"Tile sheet not found: {sheet_path}")

    sheet_surface = pygame.image.load(str(sheet_path)).convert_alpha()
    original_width, original_height = sheet_surface.get_size()

    if (
        original_width % TILESHEET_COLUMNS != 0
        or original_height % TILESHEET_ROWS != 0
    ):
        raise ValueError(
            f"Unexpected tilesheet dimensions: {original_width}x{original_height} "
            f"(expected {TILESHEET_COLUMNS}x{TILESHEET_ROWS} grid)"
        )

    base_tile_size = original_width // TILESHEET_COLUMNS
    target_size = tile_size or base_tile_size

    tiles: List[List[pygame.Surface]] = []
    for row in range(TILESHEET_ROWS):
        row_tiles: List[pygame.Surface] = []
        for col in range(TILESHEET_COLUMNS):
            rect = pygame.Rect(
                col * base_tile_size,
                row * base_tile_size,
                base_tile_size,
                base_tile_size,
            )
            tile_surface = sheet_surface.subsurface(rect).copy()
            if target_size != base_tile_size:
                # Use nearest-neighbor to preserve crisp pixels when upscaling 32->64
                tile_surface = pygame.transform.scale(
                    tile_surface,
                    (target_size, target_size),
                )
            row_tiles.append(tile_surface)
        tiles.append(row_tiles)

    return TileSheet(tiles=tiles, tile_size=target_size)


__all__ = ["TileSheet", "load_tilesheet"]
