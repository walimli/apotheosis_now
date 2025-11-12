"""Moss overlay rendering helpers.

Decodes moss overlay from encoded base tiles and renders moss as a second layer
using the existing orientation rules and soft corner helpers, without growing
chunk_renderer.py in size.
"""
from __future__ import annotations

from typing import Callable, Tuple

import numpy as np

from ..classification import classify_tiles
from ..helpers.quadrant_grid import expand_base_tiles, iter_quadrants
from ..orientation import (
    ORIENTATION_INDEX,
    ORIENTATION_SEQUENCE,
    compute_neighbor_mask,
    resolve_orientation,
)


def decode_base_and_mask(base_tiles: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return (decoded_base, moss_flags) from an encoded tile grid.

    - decoded_base: 0/1/2/3 with overlay stripped (values >=10 become v//10)
    - moss_flags: boolean mask where moss overlay is present (values >=10)
    """
    if base_tiles.ndim != 2:
        raise ValueError("base_tiles must be two-dimensional")
    encoded = np.asarray(base_tiles)
    moss_flags = encoded >= 10
    decoded = np.where(moss_flags, encoded // 10, encoded).astype(np.int8)
    return decoded, moss_flags


def render_moss_overlay(
    surface,
    moss_flags: np.ndarray,
    *,
    soft_corners,
    get_quadrant_surface: Callable[[int, int, int, bool], object],
    has_land_neighbor: Callable[[np.ndarray, int, int], bool],
    tile_size: int,
    quadrant_size: int,
) -> None:
    """Render the moss overlay onto the provided surface.

    - moss_flags: per-tile boolean mask where moss is present
    - soft_corners: SoftCornerHelper instance
    - get_quadrant_surface(biome_code, tile_type, orientation_idx, interior_edge) -> Surface
    - has_land_neighbor(classification, q_row, q_col) -> bool
    """
    rows, cols = moss_flags.shape
    if rows == 0 or cols == 0:
        return

    # Build a quadrant-resolution grid for moss
    moss_base = moss_flags.astype(np.int8, copy=False)
    q_base = expand_base_tiles(moss_base)
    q_class = classify_tiles(q_base)
    q_orient = _compute_orientations_for_overlay(q_base, q_class, soft_corners)

    # Draw moss overlay quadrants using the moss tilesheet (code 4)
    for row in range(rows):
        for col in range(cols):
            if not moss_flags[row, col]:
                continue
            for _, _, (q_offset_row, q_offset_col) in iter_quadrants():
                q_row = row * 2 + q_offset_row
                q_col = col * 2 + q_offset_col
                q_type = int(q_class[q_row, q_col])
                if q_type == 0:
                    continue

                sheet_type, sheet_index = soft_corners.variant(q_base, q_class, q_row, q_col)
                if sheet_type:
                    tile_surface = soft_corners.quadrant_surface_for_biome(4, sheet_type, sheet_index)
                else:
                    q_orientation_idx = int(q_orient[q_row, q_col])
                    interior_edge = (
                        q_type == 2 and has_land_neighbor(q_class, q_row, q_col)
                    )
                    tile_surface = get_quadrant_surface(4, q_type, q_orientation_idx, interior_edge)
                if tile_surface is None:
                    continue
                dest_x = col * tile_size + q_offset_col * quadrant_size
                dest_y = row * tile_size + q_offset_row * quadrant_size
                surface.blit(tile_surface, (dest_x, dest_y))


def _compute_orientations_for_overlay(
    base: np.ndarray,
    classification: np.ndarray,
    soft_corners,
) -> np.ndarray:
    rows, cols = classification.shape
    orientations = np.zeros((rows, cols), dtype=np.uint8)
    for r in range(rows):
        for c in range(cols):
            if base[r, c] == 0:
                orientations[r, c] = ORIENTATION_INDEX["center"]
                continue
            tile_type = int(classification[r, c])
            if tile_type == 0:
                orientations[r, c] = ORIENTATION_INDEX["center"]
                continue
            if tile_type == 1 and soft_corners.single_land_neighbor(base, r, c):
                orientations[r, c] = ORIENTATION_INDEX["center"]
            else:
                mask = compute_neighbor_mask(classification, r, c)
                orientations[r, c] = resolve_orientation(mask)
    return orientations


__all__ = [
    "decode_base_and_mask",
    "render_moss_overlay",
]

