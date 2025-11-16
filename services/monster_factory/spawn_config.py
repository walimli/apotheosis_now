"""Spawn rule dataclasses and config loading helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

RANDOMINT_RE = re.compile(r"randomint\(\s*(\d+)\s*,\s*(\d+)\s*\)", re.IGNORECASE)


@dataclass(frozen=True)
class SpawnRule:
    """Normalized rule pulled from a spawn json entry."""

    entity_id: str
    event_name: str
    spawn_chance: float
    spawn_per: str
    eligible_tiles: Optional[frozenset[int]]
    allow_shared_tile: bool
    requires_exact_position: bool
    spawn_min: int
    spawn_max: int
    player_range_tiles: Optional[Tuple[float, float]]

    def roll_count(self, rng) -> int:
        if self.spawn_min == self.spawn_max:
            return self.spawn_min
        return int(rng.randint(self.spawn_min, self.spawn_max))


class SpawnConfigLoader:
    """Lazy loader that maps event names to SpawnRule lists."""

    def __init__(self, data_root: Path) -> None:
        self._data_root = data_root
        self._event_rules: Dict[str, List[SpawnRule]] = {}
        self._spawn_files = self._discover_spawn_files()
        self._pending_files: List[Path] = list(self._spawn_files.values())

    def rules_for_event(self, event_name: str) -> List[SpawnRule]:
        normalized = self._normalize_event_name(event_name)
        if normalized not in self._event_rules and self._pending_files:
            self._load_spawn_files_until(normalized)
        return self._event_rules.get(normalized, [])

    def _discover_spawn_files(self) -> Dict[str, Path]:
        if not self._data_root.exists():
            return {}
        files: Dict[str, Path] = {}
        for path in self._data_root.glob("**/*spawn*.json"):
            if not path.is_file():
                continue
            entity_id = self._entity_id_from_filename(path)
            files[entity_id] = path
        return files

    def _load_spawn_files_until(self, target_event: str) -> None:
        while self._pending_files:
            path = self._pending_files.pop()
            self._load_spawn_file(path)
            if target_event in self._event_rules:
                return

    def _load_spawn_file(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_events = data.get("spawn_events")
        if not raw_events:
            return
        entity_id = self._entity_id_from_filename(path)
        event_map: Dict[str, Any] = {}
        if isinstance(raw_events, dict):
            event_map = raw_events
        elif isinstance(raw_events, list):
            for entry in raw_events:
                if not isinstance(entry, dict):
                    continue
                event_name = entry.get("event")
                if not event_name:
                    continue
                event_map[event_name] = entry
        else:
            raise ValueError(f"spawn_events in {path} must be dict or list")

        for event_name, payload in event_map.items():
            normalized_event = self._normalize_event_name(event_name)
            rule_entries: Sequence[Dict[str, Any]]
            if isinstance(payload, list):
                rule_entries = [entry for entry in payload if isinstance(entry, dict)]
            elif isinstance(payload, dict):
                rule_entries = [payload]
            else:
                raise ValueError(
                    f"spawn_events[{event_name}] in {path} must be dict or list"
                )
            for entry in rule_entries:
                rule = self._build_rule(entity_id, normalized_event, entry, path)
                self._event_rules.setdefault(normalized_event, []).append(rule)

    def _build_rule(
        self,
        entity_id: str,
        event_name: str,
        payload: Dict[str, Any],
        path: Path,
    ) -> SpawnRule:
        spawn_chance = float(payload.get("spawn_chance", 1.0))
        if not 0.0 <= spawn_chance <= 1.0:
            raise ValueError(f"spawn_chance must be within [0,1] in {path}")
        spawn_per = str(payload.get("spawn_per", "island")).strip().lower()
        if spawn_per not in {"island", "void", "tile", "event"}:
            raise ValueError(f"spawn_per '{spawn_per}' invalid in {path}")

        eligible_tiles = payload.get("eligible_tiles")
        tiles_set: Optional[frozenset[int]] = None
        if eligible_tiles is not None:
            if not isinstance(eligible_tiles, Sequence):
                raise ValueError(f"eligible_tiles must be a sequence in {path}")
            tiles_set = frozenset(int(t) for t in eligible_tiles)

        spawn_min, spawn_max = self._parse_spawn_number(payload.get("spawn_number", 1))
        share_tile = self._parse_bool(payload.get("share_tile", False))
        exact_position = str(payload.get("exact_position", "pass")).strip().lower()
        requires_exact_position = exact_position not in {"pass", "", "ignore"}
        player_range = payload.get("player_range")
        player_range_tiles = (
            self._parse_player_range(player_range, path) if player_range is not None else None
        )

        return SpawnRule(
            entity_id=entity_id,
            event_name=event_name,
            spawn_chance=spawn_chance,
            spawn_per=spawn_per,
            eligible_tiles=tiles_set,
            allow_shared_tile=share_tile,
            requires_exact_position=requires_exact_position,
            spawn_min=spawn_min,
            spawn_max=spawn_max,
            player_range_tiles=player_range_tiles,
        )

    def _entity_id_from_filename(self, path: Path) -> str:
        stem = path.stem
        lowered = stem.lower()
        if "_spawn" in lowered:
            idx = lowered.rfind("_spawn")
            return stem[:idx]
        return stem

    def _parse_spawn_number(self, raw_value: Any) -> Tuple[int, int]:
        if isinstance(raw_value, (int, float)):
            value = int(raw_value)
            return (value, value)
        if isinstance(raw_value, str):
            match = RANDOMINT_RE.match(raw_value.strip())
            if not match:
                raise ValueError(f"Unsupported spawn_number expression '{raw_value}'")
            start, end = int(match.group(1)), int(match.group(2))
            low, high = sorted((start, end))
            return (low, high)
        raise ValueError(f"spawn_number '{raw_value}' is not supported")

    def _parse_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return False

    def _parse_player_range(self, value: Any, path: Path) -> Tuple[float, float]:
        if not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError(f"player_range in {path} must be a 2-length sequence")
        min_val = float(value[0])
        max_val = float(value[1])
        if min_val < 0:
            min_val = 0.0
        if max_val < 0:
            max_val = 0.0
        low, high = sorted((min_val, max_val))
        return (low, high if high > 0 else float("inf"))

    def _normalize_event_name(self, name: str) -> str:
        return str(name or "").strip().lower()


__all__ = ["SpawnRule", "SpawnConfigLoader"]
