"""Pill registry for placement service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class PillSpec:
    item_id: str
    effect: str
    magnitude: int


class PillRegistry:
    """Lookup pill metadata from medallion inventory data."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        root = Path(project_root or Path(__file__).resolve().parents[2])
        self._path = root / "data" / "inventory" / "medallions.json"
        self._cache: Dict[str, PillSpec] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if not self._path.is_file():
            self._cache.clear()
            self._loaded = True
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        items = payload.get("inventory_items", [])
        cache: Dict[str, PillSpec] = {}
        for entry in items:
            if not isinstance(entry, dict):
                continue
            if not entry.get("pill"):
                continue
            item_id = str(entry.get("id", "")).strip()
            effect = str(entry.get("pill_effect", "")).strip().lower()
            magnitude = int(entry.get("pill_magnitude", 0))
            if not item_id or not effect or magnitude <= 0:
                continue
            cache[item_id] = PillSpec(
                item_id=item_id,
                effect=effect,
                magnitude=magnitude,
            )
        self._cache = cache
        self._loaded = True

    def get(self, item_id: str) -> Optional[PillSpec]:
        self._ensure_loaded()
        return self._cache.get(item_id)

    def is_pill(self, item_id: str) -> bool:
        return self.get(item_id) is not None


__all__ = ["PillRegistry", "PillSpec"]
