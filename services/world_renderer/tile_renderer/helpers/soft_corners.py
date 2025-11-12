"""Soft corner detection and rendering helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pygame


class SoftCornerHelper:
    """Load soft-corner sheets and resolve variants for eligible tiles."""

    _INTERIOR = 1
    _EXTERIOR = 2

    def __init__(self, tile_size: int, asset_root: Path) -> None:
        if tile_size % 2 != 0:
            raise ValueError("tile_size must be divisible by 2 for soft corner quadrants")
        self.tile_size = tile_size
        self._interior_sheet = self._load_corner_sheet(asset_root / "interior_soft_corners.png")
        self._exterior_sheet = self._load_corner_sheet(asset_root / "exterior_soft_corners.png")
        self._quadrant_size = max(1, self.tile_size // 2)
        self._quadrant_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._biome_corner_sheets: Dict[Tuple[int, int], list[list[pygame.Surface]]] = {}
        self._biome_quadrant_cache: Dict[Tuple[int, int, int], pygame.Surface] = {}
        # Load biome-specific soft corner sheets (red=2, stone=3, moss=4)
        self._load_biome_corners(asset_root)

    def single_land_neighbor(self, base_tiles: np.ndarray, row: int, col: int) -> bool:
        """Return True when a land tile connects to only one neighbor (including diagonals)."""
        rows, cols = base_tiles.shape
        count = 0
        for n_row in range(row - 1, row + 2):
            for n_col in range(col - 1, col + 2):
                if n_row == row and n_col == col:
                    continue
                if 0 <= n_row < rows and 0 <= n_col < cols:
                    if base_tiles[n_row, n_col] != 0:
                        count += 1
                        if count > 1:
                            return False
        return count == 1

    def variant(
        self,
        base_tiles: np.ndarray,
        classification: np.ndarray,
        row: int,
        col: int,
    ) -> Tuple[int, int]:
        """Return (sheet_type, index) for soft corner sprites or (0, 0) if not applicable."""
        rows, cols = base_tiles.shape
        # All orthogonal neighbors must be present
        for d_row, d_col in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            n_row = row + d_row
            n_col = col + d_col
            if not (0 <= n_row < rows and 0 <= n_col < cols):
                return (0, 0)
            if base_tiles[n_row, n_col] == 0:
                return (0, 0)

        diagonals = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        empty_diagonals = []
        for d_row, d_col in diagonals:
            n_row = row + d_row
            n_col = col + d_col
            class_value = 0
            if 0 <= n_row < rows and 0 <= n_col < cols:
                if base_tiles[n_row, n_col] != 0:
                    continue
                class_value = int(classification[n_row, n_col])
            empty_diagonals.append((d_row, d_col, class_value))

        empty_diagonals = [entry for entry in empty_diagonals if entry is not None]
        if len(empty_diagonals) != 1:
            return (0, 0)

        d_row, d_col, class_value = empty_diagonals[0]
        index = self._index_for_offset(d_row, d_col)
        if index is None:
            return (0, 0)

        sheet_type = self._EXTERIOR if class_value == 0 else self._INTERIOR
        return (sheet_type, index)

    def surface(self, sheet_type: int, index: int) -> pygame.Surface | None:
        """Return the pre-scaled surface for the given corner sheet/index."""
        if sheet_type == self._INTERIOR:
            index = {0: 3, 1: 2, 2: 1, 3: 0}[index]
            sheet = self._interior_sheet
        elif sheet_type == self._EXTERIOR:
            sheet = self._exterior_sheet
        else:
            return None

        row = 0 if index in (0, 1) else 1
        col = 0 if index in (0, 2) else 1
        return sheet[row][col]

    def quadrant_surface(self, sheet_type: int, index: int) -> pygame.Surface | None:
        """Return a quadrant-sized surface for the given sheet/index."""
        key = (sheet_type, index)
        if key in self._quadrant_cache:
            return self._quadrant_cache[key]
        base_surface = self.surface(sheet_type, index)
        if base_surface is None:
            return None

        quadrant_surface = pygame.transform.scale(
            base_surface,
            (self._quadrant_size, self._quadrant_size),
        )
        self._quadrant_cache[key] = quadrant_surface
        return quadrant_surface

    def quadrant_surface_for_biome(self, biome_code: int, sheet_type: int, index: int) -> pygame.Surface | None:
        """Return a quadrant-sized corner surface for the tile's biome.

        Selection logic (variant/index) is unchanged; only the source sheet differs
        per biome. Biome 1 (clay) uses the default sheets; redrock (2), stone (3),
        and moss (4) use their own interior/exterior soft-corner sheets.
        """
        if biome_code == 1:
            return self.quadrant_surface(sheet_type, index)
        # Apply the same interior index remap used by surface() for consistency
        if sheet_type == self._INTERIOR:
            index = {0: 3, 1: 2, 2: 1, 3: 0}[index]
        key = (biome_code, sheet_type, index)
        if key in self._biome_quadrant_cache:
            return self._biome_quadrant_cache[key]
        grid = self._biome_corner_sheets.get((biome_code, sheet_type))
        if grid is None:
            raise FileNotFoundError(
                f"Corner sheet not loaded for biome {biome_code} and sheet {sheet_type}"
            )
        # Map index to 2x2 grid (matches surface() mapping)
        mapped = {0: (0, 0), 1: (0, 1), 2: (1, 0), 3: (1, 1)}
        r, c = mapped.get(index, (0, 0))
        base_surface = grid[r][c]
        if base_surface is None:
            return None
        if (
            base_surface.get_width() == self._quadrant_size
            and base_surface.get_height() == self._quadrant_size
        ):
            self._biome_quadrant_cache[key] = base_surface
            return base_surface
        quadrant_surface = pygame.transform.scale(
            base_surface,
            (self._quadrant_size, self._quadrant_size),
        )
        self._biome_quadrant_cache[key] = quadrant_surface
        return quadrant_surface

    def _load_biome_corners(self, asset_root: Path) -> None:
        mapping = {
            2: ("red_tiles", "red"),
            3: ("stone_tiles", "stone"),
            4: ("moss_tiles", "moss"),
        }
        for code, (folder, name) in mapping.items():
            interior = asset_root / "biomes" / folder / f"{name}_interior_soft_corners.png"
            exterior = asset_root / "biomes" / folder / f"{name}_exterior_soft_corners.png"
            if not interior.exists() or not exterior.exists():
                raise FileNotFoundError(
                    f"Missing soft corner sheets for biome {code}: {interior} or {exterior}"
                )
            self._biome_corner_sheets[(code, self._INTERIOR)] = self._load_corner_sheet(interior)
            self._biome_corner_sheets[(code, self._EXTERIOR)] = self._load_corner_sheet(exterior)

    

    def _load_corner_sheet(self, path: Path) -> list[list[pygame.Surface]]:
        if not path.exists():
            raise FileNotFoundError(f"Corner sheet not found: {path}")
        sheet = pygame.image.load(str(path)).convert_alpha()
        base_size = sheet.get_width() // 2
        tiles: list[list[pygame.Surface]] = []
        for r in range(2):
            row_tiles: list[pygame.Surface] = []
            for c in range(2):
                rect = pygame.Rect(c * base_size, r * base_size, base_size, base_size)
                tile_surface = sheet.subsurface(rect).copy()
                if base_size != self.tile_size:
                    tile_surface = pygame.transform.scale(
                        tile_surface,
                        (self.tile_size, self.tile_size),
                    )
                row_tiles.append(tile_surface)
            tiles.append(row_tiles)
        return tiles

    @staticmethod
    def _index_for_offset(d_row: int, d_col: int) -> int | None:
        mapping = {
            (1, 1): 3,    # missing top-left
            (1, -1): 2,   # missing top-right
            (-1, 1): 1,   # missing bottom-left
            (-1, -1): 0,  # missing bottom-right
        }
        return mapping.get((d_row, d_col))


__all__ = ["SoftCornerHelper"]
