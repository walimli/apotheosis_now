"""Asset helpers for the rune background animation."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List, Tuple

import pygame

_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

_ASSET_ROOT = os.path.join(
    _PACKAGE_ROOT,
    "assets",
    "effects",
    "runes",
)

_FRAME_DIRS = {
    "first": os.path.join(_ASSET_ROOT, "first_frame"),
    "second": os.path.join(_ASSET_ROOT, "second_frame"),
    "third": os.path.join(_ASSET_ROOT, "third_frame"),
}


def _extract_index(filename: str) -> int | None:
    digits = [ch for ch in filename if ch.isdigit()]
    if not digits:
        return None
    return int("".join(digits))


def _load_frame_map(folder: str) -> Dict[int, pygame.Surface]:
    mapping: Dict[int, pygame.Surface] = {}
    for entry in os.listdir(folder):
        if not entry.lower().endswith(".png"):
            continue
        index = _extract_index(entry)
        if index is None:
            continue
        path = os.path.join(folder, entry)
        surface = pygame.image.load(path).convert_alpha()
        mapping[index] = surface
    return mapping


@lru_cache(maxsize=1)
def load_rune_triplets() -> List[Tuple[pygame.Surface, pygame.Surface, pygame.Surface]]:
    """Load and return the rune frames grouped as animation triplets."""
    first = _load_frame_map(_FRAME_DIRS["first"])
    second = _load_frame_map(_FRAME_DIRS["second"])
    third = _load_frame_map(_FRAME_DIRS["third"])
    common_indices = sorted(set(first) & set(second) & set(third))
    triplets: List[Tuple[pygame.Surface, pygame.Surface, pygame.Surface]] = []
    for idx in common_indices:
        triplets.append((first[idx], second[idx], third[idx]))
    return triplets
