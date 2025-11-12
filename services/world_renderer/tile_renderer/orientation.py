"""Orientation helpers for chunk tile rendering."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

EDGE_COORDS: Dict[str, Tuple[int, int]] = {
    "center": (2, 2),
    "top": (0, 2),
    "right": (2, 4),
    "bottom": (4, 2),
    "left": (2, 0),
    "top_left": (0, 0),
    "top_right": (0, 4),
    "bottom_left": (4, 0),
    "bottom_right": (4, 4),
}

ORIENTATION_SEQUENCE = [
    "center",
    "top",
    "right",
    "bottom",
    "left",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
]
ORIENTATION_INDEX = {name: idx for idx, name in enumerate(ORIENTATION_SEQUENCE)}


def compute_neighbor_mask(classification: np.ndarray, row: int, col: int) -> int:
    """Return a 4-bit mask describing which orthogonal neighbors share the tile class."""
    tile_type = int(classification[row, col])
    rows, cols = classification.shape
    mask = 0
    if row > 0 and classification[row - 1, col] == tile_type:
        mask |= 0b0001
    if col + 1 < cols and classification[row, col + 1] == tile_type:
        mask |= 0b0010
    if row + 1 < rows and classification[row + 1, col] == tile_type:
        mask |= 0b0100
    if col > 0 and classification[row, col - 1] == tile_type:
        mask |= 0b1000
    return mask


def resolve_orientation(mask: int) -> int:
    """Translate a neighbor mask into an orientation index."""
    void_mask = (~mask) & 0b1111
    lookup = {
        0: "center",
        0b0001: "top",
        0b0010: "right",
        0b0100: "bottom",
        0b1000: "left",
        0b0011: "top_right",
        0b0110: "bottom_right",
        0b1100: "bottom_left",
        0b1001: "top_left",
    }

    if void_mask in lookup:
        return ORIENTATION_INDEX[lookup[void_mask]]

    same_count = bin(mask).count("1")
    if same_count == 0:
        return ORIENTATION_INDEX["center"]

    if same_count == 1:
        if mask & 0b0001:
            return ORIENTATION_INDEX["bottom"]
        if mask & 0b0010:
            return ORIENTATION_INDEX["left"]
        if mask & 0b0100:
            return ORIENTATION_INDEX["top"]
        return ORIENTATION_INDEX["right"]

    if void_mask == 0b0101:
        return ORIENTATION_INDEX["top"]
    if void_mask == 0b1010:
        return ORIENTATION_INDEX["left"]

    if void_mask in (0b0111, 0b1011, 0b1101, 0b1110):
        if mask & 0b0001:
            return ORIENTATION_INDEX["top"]
        if mask & 0b0010:
            return ORIENTATION_INDEX["right"]
        if mask & 0b0100:
            return ORIENTATION_INDEX["bottom"]
        return ORIENTATION_INDEX["left"]

    return ORIENTATION_INDEX["center"]


__all__ = [
    "EDGE_COORDS",
    "ORIENTATION_INDEX",
    "ORIENTATION_SEQUENCE",
    "compute_neighbor_mask",
    "resolve_orientation",
]
