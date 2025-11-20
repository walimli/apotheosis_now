"""Fence data accessors that bridge placement logic with JSON datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterator, List, Mapping, Optional, Tuple

from systems.placeables.placeables_json_reader import (
    PlaceableDataset,
    PlaceableRecord,
    PlaceablesJsonReader,
)

VariantKey = str
ItemId = str

FenceVariantMap = Dict[VariantKey, "FenceVariant"]
ItemVariantLookup = Dict[ItemId, Tuple[VariantKey, ...]]

DATASET_ITEM_MAP: Mapping[str, ItemId] = {
    "wood_fence": "wood_fence_coin",
    "stone_fence": "stone_fence_coin",
}


@dataclass(frozen=True)
class FenceVariant:
    """Normalised metadata linking a fence variant to its source record."""

    key: VariantKey
    variant_id: str
    dataset: str
    item_id: ItemId
    record: PlaceableRecord

    @property
    def image_path(self) -> str:
        return self.record.image_path

    @property
    def asset_key(self) -> str:
        # Use image_path to ensure uniqueness across fence families.
        return self.record.image_path

    @property
    def connecting_edges(self) -> Tuple[str, ...]:
        return tuple(self.record.connecting_edges)

    @property
    def collision_polygon(self) -> Optional[Tuple[Tuple[float, float], ...]]:
        return self.record.collision_polygon

    @property
    def collision_offsets(self) -> Tuple[float, float]:
        return self.record.collision_offsets

    @property
    def scale(self) -> float:
        return self.record.scale


_variant_cache: FenceVariantMap | None = None
_item_lookup: ItemVariantLookup | None = None
_reader: PlaceablesJsonReader | None = None


def _ensure_reader() -> PlaceablesJsonReader:
    global _reader
    if _reader is None:
        _reader = PlaceablesJsonReader()
    return _reader


def _normalise_record(
    dataset_name: str, item_id: ItemId, record: PlaceableRecord
) -> FenceVariant:
    variant_id = record.variant_id or record.key
    unique_key = f"{item_id}:{variant_id}"
    return FenceVariant(
        key=unique_key,
        variant_id=str(variant_id),
        dataset=dataset_name,
        item_id=item_id,
        record=record,
    )


def _build_cache() -> None:
    global _variant_cache, _item_lookup
    reader = _ensure_reader()
    variant_map: FenceVariantMap = {}
    item_map: ItemVariantLookup = {}
    for dataset_name, item_id in DATASET_ITEM_MAP.items():
        dataset = _load_dataset(reader, dataset_name)
        variants: List[VariantKey] = []
        for record in dataset.entries:
            variant = _normalise_record(dataset_name, item_id, record)
            variant_map[variant.key] = variant
            variants.append(variant.key)
        item_map[item_id] = tuple(variants)
    _variant_cache = variant_map
    _item_lookup = item_map


def _load_dataset(reader: PlaceablesJsonReader, name: str) -> PlaceableDataset:
    try:
        return reader.load_dataset(name)
    except FileNotFoundError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(f"Fence dataset '{name}' could not be loaded") from exc


def _cached_variants() -> FenceVariantMap:
    if _variant_cache is None or _item_lookup is None:
        _build_cache()
    return _variant_cache or {}


def _cached_item_lookup() -> ItemVariantLookup:
    if _variant_cache is None or _item_lookup is None:
        _build_cache()
    return _item_lookup or {}


def get_variant(variant_key: VariantKey) -> Optional[FenceVariant]:
    """Return the normalised fence variant, if present."""
    return _cached_variants().get(variant_key)


def get_variant_meta(variant_key: VariantKey) -> Optional[Dict[str, object]]:
    """Legacy helper returning dict metadata for compatibility layers."""
    variant = get_variant(variant_key)
    if variant is None:
        return None
    polygon = variant.collision_polygon
    offsets = variant.collision_offsets
    return {
        "variant_key": variant.key,
        "variant_id": variant.variant_id,
        "dataset": variant.dataset,
        "item_id": variant.item_id,
        "asset_key": variant.asset_key,
        "connecting_edges": tuple(variant.connecting_edges),
        "collision_polygon": tuple(polygon) if polygon else (),
        "collision_offsets": {"x": float(offsets[0]), "y": float(offsets[1])},
        "scale": float(variant.scale),
    }


def get_connecting_edges(meta: Mapping[str, object]) -> Tuple[str, ...]:
    """Extract connecting edge labels from metadata."""
    raw = meta.get("connecting_edges", ())
    if isinstance(raw, (list, tuple)):
        return tuple(str(edge) for edge in raw)
    return tuple()


def iter_variants() -> Iterator[Tuple[VariantKey, FenceVariant]]:
    """Iterate over all cached fence variants."""
    return iter(_cached_variants().items())


def all_variant_keys() -> Tuple[VariantKey, ...]:
    """Return the variant keys that are currently registered."""
    return tuple(_cached_variants().keys())


def variants_for_item(item_id: ItemId) -> Tuple[VariantKey, ...]:
    """Return variant keys available for a given fence item id."""
    lookup = _cached_item_lookup()
    return lookup.get(item_id, tuple())


def reset_cache() -> None:
    """Clear cached definitions (useful for hot-reload in development)."""
    global _variant_cache, _item_lookup
    _variant_cache = None
    _item_lookup = None
