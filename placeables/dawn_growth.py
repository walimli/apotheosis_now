from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from .placeables_json_reader import PlaceableDataset, PlaceableRecord


StageKey = Tuple[str, str]  # (dataset_name, record_key)


@dataclass(frozen=True)
class GrowthStep:
    current: PlaceableRecord
    next: PlaceableRecord
    dataset: PlaceableDataset


class DawnGrowthController:
    """Handle dawn-growth lifecycle progression for multi-stage placeables."""

    def __init__(self, dataset_loader: Callable[[str], PlaceableDataset]) -> None:
        self._load_dataset = dataset_loader
        self._order_cache: Dict[str, Tuple[str, ...]] = {}

    def has_next_stage(self, dataset_name: str, record_key: str) -> bool:
        dataset = self._load_dataset(dataset_name)
        order = self._dataset_order(dataset)
        try:
            index = order.index(record_key)
        except ValueError:
            return False
        return index + 1 < len(order)

    def next_step(
        self, dataset_name: str, record_key: str
    ) -> Optional[GrowthStep]:
        dataset = self._load_dataset(dataset_name)
        order = self._dataset_order(dataset)
        try:
            index = order.index(record_key)
        except ValueError:
            return None
        if index + 1 >= len(order):
            return None
        next_key = order[index + 1]
        current_record = dataset.get(record_key)
        next_record = dataset.get(next_key)
        if not current_record.dawn_growth:
            return None
        return GrowthStep(current=current_record, next=next_record, dataset=dataset)

    def initial_record(self, dataset_name: str) -> PlaceableRecord:
        dataset = self._load_dataset(dataset_name)
        order = self._dataset_order(dataset)
        first_key = order[0]
        return dataset.get(first_key)

    def _dataset_order(self, dataset: PlaceableDataset) -> Tuple[str, ...]:
        cached = self._order_cache.get(dataset.name)
        if cached is not None:
            return cached
        order = dataset.order
        if not order:
            order = tuple(record.key for record in dataset.entries)
        self._order_cache[dataset.name] = order
        return order


__all__ = ["DawnGrowthController", "GrowthStep"]
