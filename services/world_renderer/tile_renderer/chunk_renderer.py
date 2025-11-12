"""Chunk tile rendering helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pygame

from services.asset_loader.tiles import TileSheet

from .classification import classify_tiles
from .helpers.quadrant_grid import expand_base_tiles, iter_quadrants
from .helpers.soft_corners import SoftCornerHelper
from .orientation import (
    EDGE_COORDS,
    ORIENTATION_INDEX,
    ORIENTATION_SEQUENCE,
    compute_neighbor_mask,
    resolve_orientation,
)
from .overlay.moss_overlay import decode_base_and_mask, render_moss_overlay

ChunkKey = Tuple[int, int]


@dataclass(slots=True)
class TileRenderData:
    """Bundled tile metadata and rendered surface for a chunk."""

    surface: pygame.Surface
    classification: np.ndarray
    orientations: np.ndarray
    moss_flags: np.ndarray


@dataclass(slots=True)
class QuadrantGrids:
    """High-resolution tile data derived from a coarse chunk grid."""

    base: np.ndarray
    classification: np.ndarray
    orientations: np.ndarray


class ChunkTileRenderer:
    """Convert logical chunk tiles into rendered Surfaces and metadata."""

    _CORNER_INTERIOR = 1
    _CORNER_EXTERIOR = 2

    def __init__(
        self,
        tile_sheet: TileSheet,
        *,
        tile_size: int,
        chunk_size: int,
        moss_probability: float = 0.05,
        moss_seed: int = 0,
    ) -> None:
        if tile_size <= 0:
            raise ValueError("tile_size must be a positive integer")
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        if tile_size % 2 != 0:
            raise ValueError("tile_size must be divisible by 2 for quadrant rendering")

        self.tile_sheet = tile_sheet
        self.tile_size = tile_size
        self.chunk_size = chunk_size

        asset_root = Path(__file__).resolve().parents[3] / "assets" / "tiles"
        self._soft_corners = SoftCornerHelper(tile_size, asset_root)
        self._quadrant_size = max(1, self.tile_size // 2)

        # Water base
        water_asset_dir = asset_root / "water_animation"
        water_tile_path = water_asset_dir / "water_tile.png"
        if not water_tile_path.exists():
            raise FileNotFoundError(f"Water tile not found: {water_tile_path}")
        water_tile = pygame.image.load(str(water_tile_path)).convert_alpha()
        if water_tile.get_width() != self.tile_size or water_tile.get_height() != self.tile_size:
            water_tile = pygame.transform.scale(water_tile, (self.tile_size, self.tile_size))
        self._water_tile = water_tile

        # Biome tilesheets (code -> grid of surfaces)
        self._biome_grids: Dict[int, list[list[pygame.Surface]]] = {}
        # 1 (clay) uses the shared TileSheet
        # 2 redrock, 3 stone, 4 moss use dedicated sheets under assets/tiles/biomes
        self._load_biome_sheets(asset_root)

        # Per-biome corner sheets

        # Caches
        self._quadrant_surface_cache: Dict[Tuple[int, int, int], pygame.Surface] = {}

        # Preload interior blank (from clay sheet coordinates)
        self._interior_blank_surface = self.tile_sheet.get(2, 7)
        self._quadrant_blank_surface = pygame.transform.scale(
            self._interior_blank_surface,
            (self._quadrant_size, self._quadrant_size),
        )

    def render(
        self,
        chunk_key: ChunkKey,
        base_tiles: np.ndarray,
        *,
        existing_moss: np.ndarray | None = None,
    ) -> TileRenderData:
        """Return rendered surface and metadata for the chunk tiles."""
        # Decode overlay moss (>=10) into base (0/1/2/3) and moss mask
        decoded_base, moss_flags = decode_base_and_mask(base_tiles)
        classification = classify_tiles(decoded_base)
        orientations, _ = self._compute_orientations(
            chunk_key,
            decoded_base,
            classification,
            enable_moss=False,
            cell_scale=1,
            existing_moss=None,
        )
        quadrant_grids = self._prepare_quadrant_grids(chunk_key, decoded_base)
        surface = self._render_surface(
            chunk_key,
            decoded_base,
            classification,
            orientations,
            quadrant_grids,
            moss_flags,
        )
        # Render moss overlay on top (uses tilesheet code 4)
        render_moss_overlay(
            surface,
            moss_flags,
            soft_corners=self._soft_corners,
            get_quadrant_surface=lambda biome_code, tile_type, orient_idx, interior: self._quadrant_surface_for(
                biome_code,
                tile_type,
                orient_idx,
                interior,
            ),
            has_land_neighbor=self._has_land_neighbor,
            tile_size=self.tile_size,
            quadrant_size=self._quadrant_size,
        )
        return TileRenderData(
            surface,
            classification,
            orientations,
            moss_flags,
        )

    def _prepare_quadrant_grids(
        self,
        chunk_key: ChunkKey,
        base_tiles: np.ndarray,
    ) -> QuadrantGrids:
        quadrant_base = expand_base_tiles(base_tiles)
        quadrant_classification = classify_tiles(quadrant_base)
        quadrant_orientations, _ = self._compute_orientations(
            chunk_key,
            quadrant_base,
            quadrant_classification,
            enable_moss=False,
            cell_scale=2,
        )
        return QuadrantGrids(
            base=quadrant_base,
            classification=quadrant_classification,
            orientations=quadrant_orientations,
        )

    def _compute_orientations(
        self,
        chunk_key: ChunkKey,
        base_tiles: np.ndarray,
        classification: np.ndarray,
        *,
        enable_moss: bool,
        cell_scale: int,
        existing_moss: np.ndarray | None = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        rows, cols = classification.shape
        orientations = np.zeros((rows, cols), dtype=np.uint8)
        moss_flags = np.zeros((rows, cols), dtype=bool)

        for row in range(rows):
            for col in range(cols):
                if base_tiles[row, col] == 0:
                    orientations[row, col] = ORIENTATION_INDEX["center"]
                    continue
                tile_type = int(classification[row, col])
                if tile_type == 0:
                    orientations[row, col] = ORIENTATION_INDEX["center"]
                    continue
                if tile_type == 1 and self._soft_corners.single_land_neighbor(base_tiles, row, col):
                    orientations[row, col] = ORIENTATION_INDEX["center"]
                else:
                    mask = compute_neighbor_mask(classification, row, col)
                    orientations[row, col] = resolve_orientation(mask)
                if enable_moss:
                    moss_flags[row, col] = int(base_tiles[row, col]) == 4
        return orientations, moss_flags

    def _render_surface(
        self,
        chunk_key: ChunkKey,
        base_tiles: np.ndarray,
        classification: np.ndarray,
        orientations: np.ndarray,
        quadrant_grids: QuadrantGrids,
        moss_flags: np.ndarray,
    ) -> pygame.Surface:
        rows, cols = classification.shape
        surface = pygame.Surface((cols * self.tile_size, rows * self.tile_size), pygame.SRCALPHA)

        quadrant_classification = quadrant_grids.classification
        quadrant_orientations = quadrant_grids.orientations

        for row in range(rows):
            for col in range(cols):
                biome_code = int(base_tiles[row, col])
                if biome_code == 0:
                    continue
                for quadrant_idx, _, (q_offset_row, q_offset_col) in iter_quadrants():
                    q_row = row * 2 + q_offset_row
                    q_col = col * 2 + q_offset_col
                    q_tile_type = int(quadrant_classification[q_row, q_col])
                    if q_tile_type == 0:
                        continue

                    sheet_type, sheet_index = self._soft_corners.variant(
                        quadrant_grids.base,
                        quadrant_classification,
                        q_row,
                        q_col,
                    )
                    if sheet_type:
                        tile_surface = self._soft_corners.quadrant_surface_for_biome(biome_code, sheet_type, sheet_index)
                    else:
                        q_orientation_idx = int(quadrant_orientations[q_row, q_col])
                        interior_edge = (
                            q_tile_type == 2 and self._has_land_neighbor(quadrant_classification, q_row, q_col)
                        )
                        tile_surface = self._quadrant_surface_for(
                            biome_code,
                            q_tile_type,
                            q_orientation_idx,
                            interior_edge,
                        )
                    if tile_surface is None:
                        continue
                    dest_x = col * self.tile_size + q_offset_col * self._quadrant_size
                    dest_y = row * self.tile_size + q_offset_row * self._quadrant_size
                    surface.blit(tile_surface, (dest_x, dest_y))
        return surface

    def _quadrant_surface_for(
        self,
        biome_code: int,
        tile_type: int,
        orientation_idx: int,
        interior_edge: bool,
    ) -> pygame.Surface | None:
        if tile_type == 0:
            return None
        orientation_key = ORIENTATION_SEQUENCE[orientation_idx]
        row, col = EDGE_COORDS[orientation_key]
        if tile_type == 1:
            offset_col = col
        else:
            if interior_edge:
                offset_col = col + 5
            else:
                return self._quadrant_blank_surface
        return self._get_quadrant_surface(biome_code, row, offset_col)

    def _get_quadrant_surface(self, biome_code: int, row: int, col: int) -> pygame.Surface:
        key = (biome_code, row, col)
        surface = self._quadrant_surface_cache.get(key)
        if surface is not None:
            return surface
        base_surface = self._biome_base_surface(biome_code, row, col)
        quadrant_surface = pygame.transform.scale(
            base_surface,
            (self._quadrant_size, self._quadrant_size),
        )
        self._quadrant_surface_cache[key] = quadrant_surface
        return quadrant_surface

    def _biome_base_surface(self, biome_code: int, row: int, col: int) -> pygame.Surface:
        if biome_code == 1:
            return self.tile_sheet.get(row, col)
        grid = self._biome_grids.get(biome_code)
        if grid is None:
            raise KeyError(f"Missing tilesheet for biome code {biome_code}")
        return grid[row][col]

    
    @staticmethod
    def _has_land_neighbor(classification: np.ndarray, row: int, col: int) -> bool:
        rows, cols = classification.shape
        for n_row, n_col in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ):
            if 0 <= n_row < rows and 0 <= n_col < cols:
                if classification[n_row, n_col] == 1:
                    return True
        return False

    def _load_biome_sheets(self, asset_root: Path) -> None:
        # redrock (2), stone (3), moss (4)
        mapping = {
            2: asset_root / 'biomes' / 'red_tiles' / 'red_tilesheet.png',
            3: asset_root / 'biomes' / 'stone_tiles' / 'stone_tilesheet.png',
            4: asset_root / 'biomes' / 'moss_tiles' / 'moss_tilesheet.png',
        }
        for code, path in mapping.items():
            if not path.exists():
                raise FileNotFoundError(f"Biome tilesheet missing: {path}")
            self._biome_grids[code] = self._slice_grid(path)

    def _slice_grid(self, image_path: Path, *, rows: int = 5, cols: int = 10) -> list[list[pygame.Surface]]:
        surf = pygame.image.load(str(image_path)).convert_alpha()
        w, h = surf.get_size()
        tile_w = w // cols
        tile_h = h // rows
        tiles: list[list[pygame.Surface]] = []
        for r in range(rows):
            row_tiles: list[pygame.Surface] = []
            for c in range(cols):
                rect = pygame.Rect(c * tile_w, r * tile_h, tile_w, tile_h)
                cell = surf.subsurface(rect).copy()
                if tile_w != self.tile_size or tile_h != self.tile_size:
                    cell = pygame.transform.scale(cell, (self.tile_size, self.tile_size))
                row_tiles.append(cell)
            tiles.append(row_tiles)
        return tiles
    
__all__ = [
    "ChunkTileRenderer",
    "TileRenderData",
]


