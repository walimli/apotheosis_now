from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import json


@dataclass(frozen=True)
class SoundRegistry:
    events: Dict[str, Path]
    music: Dict[str, Path]

    def resolve_event(self, key: str) -> Path:
        try:
            return self.events[key]
        except KeyError as exc:
            raise KeyError(f"Unknown sound event '{key}'") from exc

    def resolve_music(self, key: str) -> Path:
        try:
            return self.music[key]
        except KeyError as exc:
            raise KeyError(f"Unknown music track '{key}'") from exc


def load_sound_registry(registry_path: Path) -> SoundRegistry:
    if not registry_path.exists():
        raise FileNotFoundError(f"Sound registry not found: {registry_path}")

    with registry_path.open("r", encoding="utf-8") as handle:
        try:
            raw = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in sound registry: {registry_path}") from exc

    if not isinstance(raw, dict):
        raise TypeError("Sound registry root must be an object")

    events = _coerce_mapping(raw.get("events"), "events")
    music = _coerce_mapping(raw.get("music"), "music")

    base_dir = registry_path.parent.parent.parent
    resolved_events = _resolve_paths(events, base_dir)
    resolved_music = _resolve_paths(music, base_dir)

    return SoundRegistry(events=resolved_events, music=resolved_music)


def _coerce_mapping(section, name: str) -> Dict[str, str]:
    if not isinstance(section, dict):
        raise TypeError(f"Sound registry section '{name}' must be an object")
    data: Dict[str, str] = {}
    for key, value in section.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"Invalid key in sound registry section '{name}': {key!r}")
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"Sound registry entry '{key}' in section '{name}' must map to a non-empty string"
            )
        if key in data:
            raise ValueError(f"Duplicate entry detected for key '{key}' in section '{name}'")
        data[key] = value
    return data


def _resolve_paths(entries: Dict[str, str], base_dir: Path) -> Dict[str, Path]:
    resolved: Dict[str, Path] = {}
    for key, rel in entries.items():
        path = (base_dir / rel).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Sound file for '{key}' not found: {path}")
        resolved[key] = path
    return resolved
