from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any

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


def _inventory_data_paths() -> list[Path]:
    """Return absolute paths to all inventory JSON files."""
    data_dir = _project_root() / "data" / "inventory"
    return [
        data_dir / "coins.json",
        data_dir / "medallions.json",
    ]


def _merge_with_defaults(
    entry: Dict[str, Any], defaults: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply defaults to an individual item entry, overriding only if key exists."""
    merged = defaults.copy()
    merged.update(entry)
    return merged


def load_items() -> Dict[str, ItemSpec]:
    """Load inventory items from all JSON files in data/inventory."""
    global _ITEMS, _ICONS

    items: Dict[str, ItemSpec] = {}
    project_root = _project_root()

    for json_path in _inventory_data_paths():
        if not json_path.is_file():
            raise FileNotFoundError(f"Inventory JSON not found: {json_path}")

        with json_path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)

        metadata = payload.get("metadata", {})
        defaults = metadata.get("defaults", {})

        inventory_items = payload.get("inventory_items")
        if not isinstance(inventory_items, list):
            raise ValueError(f"'inventory_items' must be a list in {json_path.name}")

        for entry in inventory_items:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid item entry in {json_path.name}")

            item_id = entry.get("id")
            if not item_id:
                raise ValueError("Item missing 'id' field")
            if item_id in items:
                raise ValueError(f"Duplicate item id '{item_id}' across JSON files")

            # Merge defaults
            full_entry = _merge_with_defaults(entry, defaults)

            image_path = full_entry.get("image_path")
            if not image_path:
                raise ValueError(f"Item '{item_id}' missing image_path")

            icon_path = (project_root / image_path).resolve()
            display_name = (
                full_entry.get("display_name") or item_id.replace("_", " ").title()
            )
            item_type = full_entry.get("item_type") or "material"

            stackable = bool(full_entry.get("stackable", True))
            stack_max_value = full_entry.get("max_stack", 64)
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
