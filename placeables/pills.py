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
    """Lookup and apply pill effects defined in the inventory registry."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self._path = self._project_root / "data" / "inventory" / "for_inventory.json"
        self._cache: Dict[str, PillSpec] = {}
        self._loaded = False

    def get(self, item_id: str) -> Optional[PillSpec]:
        if not self._loaded:
            self._load()
        return self._cache.get(item_id)

    def is_pill(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def apply(self, item_id: str, player) -> bool:
        spec = self.get(item_id)
        if spec is None:
            return False

        effect = spec.effect.lower()
        magnitude = spec.magnitude

        player_model = getattr(player, "model", player)
        if effect == "health":
            health = getattr(player_model, "health", None)
            if health is None:
                raise AttributeError("Player model missing health component for pill effect")
            healed = health.heal(magnitude)
            return healed > 0

        if effect == "soul":
            soul = getattr(player_model, "soul", None)
            if soul is None:
                raise AttributeError("Player model missing soul component for pill effect")
            restored = soul.restore(magnitude)
            return restored > 0

        raise ValueError(f"Unsupported pill effect '{spec.effect}' for item '{item_id}'")

    def _load(self) -> None:
        if not self._path.is_file():
            raise FileNotFoundError(f"Pill registry source not found: {self._path}")
        with self._path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        entries = payload.get("for_inventory")
        if not isinstance(entries, dict):
            raise ValueError("for_inventory.json missing 'for_inventory' section")

        self._cache.clear()
        for item_id, data in entries.items():
            if not isinstance(data, dict):
                continue
            if not data.get("pill"):
                continue
            effect = str(data.get("pill_effect", "")).strip()
            if not effect:
                continue
            magnitude = int(data.get("pill_magnitude", 0))
            if magnitude <= 0:
                continue
            self._cache[item_id] = PillSpec(
                item_id=item_id,
                effect=effect,
                magnitude=magnitude,
            )
        self._loaded = True


__all__ = ["PillRegistry", "PillSpec"]
