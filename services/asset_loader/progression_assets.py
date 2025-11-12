"""Asset helpers for progression state resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Sequence, Tuple

import pygame

from states.progression_state.text_content import TextContent
from states.progression_state.widgets import IconButton, SystemButton

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_ROOT = _PROJECT_ROOT / "assets"
_UI_ROOT = _ASSETS_ROOT / "ui"
_PANELS_DIR = _UI_ROOT / "panels"
_BUTTON_DIR = _UI_ROOT / "buttons" / "big_button"
_ICON_DIR = _UI_ROOT / "icons"
_PROGRESSION_ICON_DIR = _ICON_DIR / "progression_icons"
_FONT_PATH = _UI_ROOT / "fonts" / "system.ttf"

_DATA_ROOT = _PROJECT_ROOT / "data" / "messages" / "progression"


def _load_surface(path: Path) -> pygame.Surface:
    if not path.exists():
        raise FileNotFoundError(f"Missing progression asset: {path}")
    return pygame.image.load(str(path)).convert_alpha()


def load_progression_visuals(
    icon_layout: Sequence[Tuple[str, str]],
) -> Dict[str, object]:
    """Load panel, button, and icon art for the progression screen."""
    landscape_panel = _load_surface(_PANELS_DIR / "square_panel.png")
    tall_card = _load_surface(_PANELS_DIR / "tall_card.png")

    emerald_icon = _load_surface(_ICON_DIR / "emerald.png")
    emerald_icon_small = pygame.transform.smoothscale(emerald_icon, (32, 32))

    system_button = SystemButton(
        _load_surface(_BUTTON_DIR / "system_button.png"),
        _load_surface(_BUTTON_DIR / "system_hover.png"),
        _load_surface(_BUTTON_DIR / "system_press.png"),
    )

    icon_buttons: list[IconButton] = []
    for key, title in icon_layout:
        folder = _PROGRESSION_ICON_DIR / key
        default_path = folder / f"{key}.png"
        hover_path = folder / f"{key}_hover.png"
        select_path = folder / f"{key}_select.png"
        icon_buttons.append(
            IconButton(
                key,
                title,
                _load_surface(default_path),
                _load_surface(hover_path),
                _load_surface(select_path),
            )
        )

    return {
        "landscape_panel": landscape_panel,
        "tall_card": tall_card,
        "emerald_icon": emerald_icon,
        "emerald_icon_small": emerald_icon_small,
        "system_button": system_button,
        "icon_buttons": icon_buttons,
    }


def load_progression_text_entries(
    font_root: Path,
    display_service,
    icon_layout: Sequence[Tuple[str, str]],
) -> Tuple[Dict[str, TextContent], Dict[str, str], str]:
    """Load TextContent entries and icon-to-text mapping for progression."""
    text_root = progression_text_root()
    if not text_root.exists():
        raise FileNotFoundError(
            f"Missing progression text assets directory: {text_root}"
        )

    manifest = [
        ("default", "default_text.json"),
        ("might", "might_text.json"),
        ("speed", "speed_text.json"),
        ("health", "health_text.json"),
        ("formula", "formula_text.json"),
        ("fortune", "fortune_text.json"),
        ("octopus", "octopus_text.json"),
    ]

    entries: Dict[str, TextContent] = {}
    icon_map: Dict[str, str] = {}
    default_id: str | None = None

    for key, filename in manifest:
        path = text_root / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing text definition: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        text_entry = TextContent(data, font_root, display_service)
        if text_entry.id in entries:
            raise ValueError(f"Duplicate text id detected: {text_entry.id}")
        entries[text_entry.id] = text_entry
        if key == "default":
            default_id = text_entry.id
        else:
            icon_map[key] = text_entry.id

    if default_id is None:
        raise RuntimeError("Default text entry not defined")

    for key, _ in icon_layout:
        if key not in icon_map:
            raise RuntimeError(f"Missing text mapping for icon '{key}'")

    return entries, icon_map, default_id


def progression_font_path() -> Path:
    """Return the shared system font path used by the progression UI."""
    if not _FONT_PATH.exists():
        raise FileNotFoundError(f"Progression font missing: {_FONT_PATH}")
    return _FONT_PATH


def progression_text_root() -> Path:
    """Return the directory that stores progression card text definitions."""
    if not _DATA_ROOT.exists():
        raise FileNotFoundError(f"Progression text directory missing: {_DATA_ROOT}")
    return _DATA_ROOT


__all__ = [
    "load_progression_visuals",
    "load_progression_text_entries",
    "progression_font_path",
    "progression_text_root",
]
