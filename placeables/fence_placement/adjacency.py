"""Adjacency and connecting-edge logic for fence ghosts."""

from __future__ import annotations
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from . import data
from .grid import TileCoord


DEFAULT_NO_ADJACENT_IDS: Tuple[str, ...] = ("wfvcon", "wfhcon")
VARIANT_PRIORITY_IDS: Tuple[str, ...] = (
    "wfvcon",
    "wfhcon",
    "wftlc",
    "wftrc",
    "wfblc",
    "wfbrc",
    "wft",
    "wfb",
    "wfl",
    "wfr",
)


class TileLookupProtocol:
    """Minimal protocol the placed object manager must satisfy for adjacency."""

    def get_tile_entry(
        self, tile_x: int, tile_y: int
    ) -> Dict[str, Any] | None:  # pragma: no cover - protocol
        ...


EdgeSet = Tuple[str, ...]


def _entry_edges(entry: Dict[str, Any] | None) -> EdgeSet:
    if not entry:
        return tuple()
    edges = entry.get("connecting_edges")
    if not edges:
        return tuple()
    return tuple(str(edge) for edge in edges)


def collect_adjacent_edges(tile: TileCoord, tile_lookup: TileLookupProtocol) -> EdgeSet:
    """Determine which connecting edges are available around the tile."""
    tx, ty = tile
    neighbors = {
        "top": tile_lookup.get_tile_entry(tx, ty - 1),
        "bottom": tile_lookup.get_tile_entry(tx, ty + 1),
        "left": tile_lookup.get_tile_entry(tx - 1, ty),
        "right": tile_lookup.get_tile_entry(tx + 1, ty),
    }

    required: List[str] = []
    for direction, entry in neighbors.items():
        edges = _entry_edges(entry)
        if not edges:
            continue
        opposite = {
            "top": "bottom",
            "bottom": "top",
            "left": "right",
            "right": "left",
        }[direction]
        if opposite in edges:
            required.append(direction)

    return tuple(required)


def _priority_index(variant_id: str) -> int:
    try:
        return VARIANT_PRIORITY_IDS.index(variant_id)
    except ValueError:
        return len(VARIANT_PRIORITY_IDS)


def _sort_variants(keys: Iterable[str]) -> List[str]:
    ordered = []
    for key in keys:
        variant = data.get_variant(key)
        if not variant:
            continue
        ordered.append(( _priority_index(variant.variant_id), key))
    ordered.sort(key=lambda item: item[0])
    return [key for _, key in ordered]


def _fallback_variants(candidate_keys: Sequence[str]) -> List[str]:
    variants = []
    for key in candidate_keys:
        variant = data.get_variant(key)
        if not variant:
            continue
        if variant.variant_id in DEFAULT_NO_ADJACENT_IDS:
            variants.append(key)
    if variants:
        return _sort_variants(dict.fromkeys(variants))
    return _sort_variants(dict.fromkeys(candidate_keys))


def build_variant_pool(required_edges: EdgeSet, candidate_keys: Sequence[str]) -> List[str]:
    """Return variant keys that satisfy the required connecting edges."""
    if not candidate_keys:
        return []
    unique_keys = list(dict.fromkeys(candidate_keys))
    matching: List[str] = []
    for key in unique_keys:
        variant = data.get_variant(key)
        if not variant:
            continue
        edges = set(variant.connecting_edges)
        if all(edge in edges for edge in required_edges):
            matching.append(key)
    if matching:
        return _sort_variants(matching)
    return _fallback_variants(unique_keys)


def is_variant_compatible(variant_key: str, required_edges: EdgeSet) -> bool:
    """Check if a variant's connecting edges cover all required edges."""
    variant = data.get_variant(variant_key)
    if not variant:
        return False
    edges = set(variant.connecting_edges)
    return all(edge in edges for edge in required_edges)
