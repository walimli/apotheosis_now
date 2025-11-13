"""Formulas data layer: recipe loading, library, and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import json
import random


@dataclass(frozen=True)
class RecipeInput:
    item: str
    qty: int


@dataclass(frozen=True)
class Recipe:
    id: str
    inputs: Tuple[RecipeInput, ...]
    output_item: str
    output_qty: int
    success_rate: float
    health_cost: int
    soul_cost: int


class FormulasLibrary:
    """Holds all recipes and the player's known subset.

    - Loads recipe data from crafting_recipes.json
    - Maps item ids to display names using inventory JSON
    - Tracks known recipe ids and exposes sorted lists/details for UI
    """

    def __init__(
        self,
        recipes: Dict[str, Recipe],
        item_display_names: Dict[str, str],
    ) -> None:
        self._recipes = recipes
        self._item_names = item_display_names
        self.known_ids: Set[str] = set()

    # --- Construction ---
    @classmethod
    def from_files(cls, recipes_path: Path, inventory_path: Path) -> "FormulasLibrary":
        recipes = _load_recipes(recipes_path)
        item_names = _load_inventory_names(inventory_path)
        return cls(recipes, item_names)

    # --- UI accessors ---
    def all_recipes(self) -> Sequence[Recipe]:
        return list(self._recipes.values())

    def list_known_sorted(self) -> List[Recipe]:
        def display_name(recipe: Recipe) -> str:
            return self._item_names.get(recipe.output_item, recipe.output_item)

        known = [self._recipes[rid] for rid in self.known_ids if rid in self._recipes]
        known.sort(key=display_name)
        return known

    def get_details_payload(self, recipe_id: str) -> Optional[dict]:
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return None
        title = self._item_names.get(recipe.output_item, recipe.output_item)
        slots = []
        for index, inp in enumerate(recipe.inputs, start=1):
            name = self._item_names.get(inp.item, inp.item)
            slots.append(f"Slot {index}: {name}")
        return {
            "title": title,
            "slots": slots,
            "health_cost": recipe.health_cost,
            "soul_cost": recipe.soul_cost,
        }

    # --- Progression integration ---
    def grant_new_recipes(self, count: int) -> List[str]:
        if count <= 0:
            return []
        unseen = [rid for rid in self._recipes.keys() if rid not in self.known_ids]
        random.shuffle(unseen)
        grant = unseen[: max(0, min(count, len(unseen)))]
        self.known_ids.update(grant)
        return grant

    def sync_to_level(self, level: int) -> None:
        total = len(self._recipes)
        target = (level * (level + 1)) // 2
        target = min(target, total)
        if len(self.known_ids) < target:
            self.grant_new_recipes(target - len(self.known_ids))

    # --- Persistence helpers ---
    def to_dict(self) -> dict:
        return {
            "known_ids": sorted(rid for rid in self.known_ids if rid in self._recipes)
        }

    def load_from_dict(self, data: dict) -> None:
        ids = data.get("known_ids", []) if isinstance(data, dict) else []
        if not isinstance(ids, list):
            return
        valid: Set[str] = set()
        for rid in ids:
            if isinstance(rid, str) and rid in self._recipes:
                valid.add(rid)
        self.known_ids = valid


def _load_recipes(path: Path) -> Dict[str, Recipe]:
    if not path.exists():
        raise FileNotFoundError(f"Missing crafting recipes: {path}")
    with path.open("r", encoding="utf-8") as f:
        blob = json.load(f)
    if not isinstance(blob, list):
        raise TypeError("crafting_recipes.json must be a list")
    recipes: Dict[str, Recipe] = {}
    for entry in blob:
        if not isinstance(entry, dict):
            continue
        rid = str(entry.get("id", ""))
        if not rid:
            continue
        inputs_raw = entry.get("inputs", [])
        inputs: List[RecipeInput] = []
        if isinstance(inputs_raw, list):
            for node in inputs_raw:
                if not isinstance(node, dict):
                    continue
                item = str(node.get("item", ""))
                qty = int(node.get("qty", 0))
                if item and qty > 0:
                    inputs.append(RecipeInput(item=item, qty=qty))
        output_node = entry.get("output", {})
        if not isinstance(output_node, dict):
            output_node = {}
        out_item = str(output_node.get("item", ""))
        out_qty = int(output_node.get("qty", 0))
        recipe = Recipe(
            id=rid,
            inputs=tuple(inputs),
            output_item=out_item,
            output_qty=out_qty,
            success_rate=float(entry.get("success_rate", 1.0)),
            health_cost=int(entry.get("health_cost", 0)),
            soul_cost=int(entry.get("soul_cost", 0)),
        )
        recipes[rid] = recipe
    return recipes


def _load_inventory_names(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing inventory items: {path}")
    with path.open("r", encoding="utf-8") as f:
        blob = json.load(f)
    root = blob.get("for_inventory", {}) if isinstance(blob, dict) else {}
    names: Dict[str, str] = {}
    if isinstance(root, dict):
        for key, node in root.items():
            if not isinstance(node, dict):
                continue
            disp = node.get("display_name")
            if isinstance(disp, str) and disp:
                names[key] = disp
    return names


__all__ = ["FormulasLibrary", "Recipe", "RecipeInput"]

