"""Helpers for mapping world tiles to quadrant sub-cells."""
from __future__ import annotations

from typing import Iterator, Tuple

import numpy as np

# Quadrant ordering matches the clock-wise sweep starting from the north-west corner.
QUADRANT_NAMES = ("nw", "ne", "sw", "se")
QUADRANT_OFFSETS: Tuple[Tuple[int, int], ...] = (
    (0, 0),  # north-west
    (0, 1),  # north-east
    (1, 0),  # south-west
    (1, 1),  # south-east
)
QUADRANT_INDEX = {name: idx for idx, name in enumerate(QUADRANT_NAMES)}


def quadrant_shape(rows: int, cols: int) -> Tuple[int, int]:
    """Return the shape of the quadrant grid for the given coarse tile dimensions."""
    if rows < 0 or cols < 0:
        raise ValueError("rows and cols must be non-negative")
    return rows * 2, cols * 2


def quadrant_offsets(quadrant: int) -> Tuple[int, int]:
    """Return the (row, col) offset within the 2x2 tile block for the quadrant."""
    if not (0 <= quadrant < len(QUADRANT_OFFSETS)):
        raise ValueError(f"quadrant index {quadrant} out of range")
    return QUADRANT_OFFSETS[quadrant]


def quadrant_index_from_offsets(offset_row: int, offset_col: int) -> int:
    """Return the quadrant index for the provided offsets within a 2x2 block."""
    if offset_row not in (0, 1) or offset_col not in (0, 1):
        raise ValueError("offsets must be either 0 or 1 for a quadrant cell")
    return offset_row * 2 + offset_col


def tile_coords_for_quadrant(q_row: int, q_col: int) -> Tuple[int, int, int]:
    """Return (tile_row, tile_col, quadrant_index) for a quadrant grid coordinate."""
    if q_row < 0 or q_col < 0:
        raise ValueError("quadrant coordinates must be non-negative")
    tile_row = q_row // 2
    tile_col = q_col // 2
    quad_idx = quadrant_index_from_offsets(q_row % 2, q_col % 2)
    return tile_row, tile_col, quad_idx


def iter_quadrants() -> Iterator[Tuple[int, str, Tuple[int, int]]]:
    """Yield quadrants as (index, name, (row_offset, col_offset))."""
    for idx, name in enumerate(QUADRANT_NAMES):
        yield idx, name, QUADRANT_OFFSETS[idx]


def expand_base_tiles(base_tiles: np.ndarray) -> np.ndarray:
    """Return a quadrant grid with each tile replicated to its four sub-cells."""
    if base_tiles.ndim != 2:
        raise ValueError("base_tiles must be a 2D array")
    rows, cols = base_tiles.shape
    q_rows, q_cols = quadrant_shape(rows, cols)
    quadrants = np.zeros((q_rows, q_cols), dtype=base_tiles.dtype)
    for offset_row, offset_col in QUADRANT_OFFSETS:
        quadrants[offset_row::2, offset_col::2] = base_tiles
    return quadrants


__all__ = [
    "QUADRANT_INDEX",
    "QUADRANT_NAMES",
    "QUADRANT_OFFSETS",
    "expand_base_tiles",
    "iter_quadrants",
    "quadrant_index_from_offsets",
    "quadrant_offsets",
    "quadrant_shape",
    "tile_coords_for_quadrant",
]
