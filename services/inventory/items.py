from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import pygame


@dataclass(frozen=True)
class ItemSpec:
    id: str
    name: str
    item_type: str
    stack_max: int
    icon_path: str


_ITEMS: Optional[Dict[str, ItemSpec]] = None
_ICONS: Dict[str, pygame.Surface] = {}


def _project_root() -> Path:
    """Return the Bedlam project root directory."""
    return Path(__file__).resolve().parents[4]


def _inventory_data_path() -> Path:
    """Absolute path to the inventory item definitions JSON."""
    return _project_root() / "data" / "inventory" / "for_inventory.json"


def load_items() -> Dict[str, ItemSpec]:
    """Load inventory items from the data/inventory registry."""
    global _ITEMS, _ICONS

    data_path = _inventory_data_path()
    with data_path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    registry = payload.get("for_inventory")
    if not isinstance(registry, dict):
        raise ValueError("for_inventory.json missing 'for_inventory' mapping")

    items: Dict[str, ItemSpec] = {}
    project_root = _project_root()

    for item_id, entry in registry.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid entry for item '{item_id}'")

        image_path = entry.get("image_path")
        if not image_path:
            raise ValueError(f"Item '{item_id}' missing image_path")

        icon_path = (project_root / image_path).resolve()
        display_name = entry.get("display_name") or item_id.replace("_", " ").title()
        item_type = entry.get("item_type") or "material"
        stackable = bool(entry.get("stackable", False))
        stack_max_value = entry.get("max_stack", 1)
        try:
            stack_max = int(stack_max_value)
        except Exception as exc:
            raise ValueError(f"Item '{item_id}' has invalid max_stack") from exc
        if not stackable:
            stack_max = 1

        items[item_id] = ItemSpec(
            id=item_id,
            name=display_name,
            item_type=item_type,
            stack_max=stack_max,
            icon_path=str(icon_path),
        )

    _ITEMS = items
    _ICONS.clear()
    return items


def get_item(item_id: str) -> ItemSpec:
    """Get item specification by ID."""
    global _ITEMS
    if _ITEMS is None:
        load_items()
    assert _ITEMS is not None

    if item_id not in _ITEMS:
        raise KeyError(f"Unknown item id '{item_id}'")

    return _ITEMS[item_id]


def get_icon(item_id: str) -> pygame.Surface:
    """Get item icon surface, loading and caching as needed."""
    global _ICONS

    if item_id in _ICONS:
        return _ICONS[item_id]

    spec = get_item(item_id)
    icon_path = Path(spec.icon_path)

    if not icon_path.is_file():
        raise FileNotFoundError(f"Icon file not found: {icon_path}")

    surf = pygame.image.load(str(icon_path)).convert_alpha()
    _ICONS[item_id] = surf
    return surf


def get_available_items() -> Dict[str, ItemSpec]:
    """Get all available items."""
    global _ITEMS
    if _ITEMS is None:
        load_items()
    return _ITEMS.copy()


def reload_items() -> Dict[str, ItemSpec]:
    """Force reload items from registry."""
    return load_items()

