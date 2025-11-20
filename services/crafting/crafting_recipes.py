from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ecs_core.systems.soul.soul import SoulCosts
from services.inventory import items as inventory_items


@dataclass(frozen=True)
class Ingredient:
    item_id: str
    qty: int


@dataclass(frozen=True)
class CraftingRecipe:
    """Runtime representation of a crafting recipe."""

    id: str
    inputs: Tuple[Ingredient, ...]
    output_item: str
    output_qty: int
    success_rate: float
    health_cost: int
    soul_cost: int

    @property
    def unique_ingredient_count(self) -> int:
        return len({ingredient.item_id for ingredient in self.inputs})

    def matches_ordered(self, ordered_inputs: Tuple[Tuple[str, int], ...]) -> bool:
        """Check if ordered_inputs satisfy this recipe (order and qty)."""
        if len(ordered_inputs) != len(self.inputs):
            return False
        # Inputs must be in the same order and quantities must match or exceed multiples.
        for ingredient, candidate in zip(self.inputs, ordered_inputs):
            item_id, qty = candidate
            if item_id != ingredient.item_id:
                return False
            if qty < ingredient.qty:
                return False
        return True

    def max_crafts(self, ordered_inputs: Tuple[Tuple[str, int], ...]) -> int:
        """Return how many times this recipe can be crafted given ordered_inputs."""
        if len(ordered_inputs) != len(self.inputs):
            return 0
        counts: List[int] = []
        for ingredient, (item_id, qty) in zip(self.inputs, ordered_inputs):
            if item_id != ingredient.item_id:
                return 0
            if ingredient.qty <= 0:
                return 0
            counts.append(qty // ingredient.qty)
        return min(counts) if counts else 0


class CraftingRecipes:
    """Loader/registry for crafting recipes defined in JSON."""

    def __init__(self, *, json_path: Optional[Path] = None) -> None:
        if json_path is None:
            json_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "formulas"
                / "crafting_recipes.json"
            )
        self._json_path = json_path
        self._recipes: Dict[str, CraftingRecipe] = {}
        self._loaded = False

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        if not self._json_path.exists():
            raise FileNotFoundError(f"Crafting recipes JSON missing: {self._json_path}")
        with self._json_path.open("r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
        if not isinstance(raw_data, list):
            raise ValueError("crafting_recipes.json must contain a list of recipes")

        recipes: Dict[str, CraftingRecipe] = {}
        for entry in raw_data:
            recipe = self._parse_recipe(entry)
            if recipe.id in recipes:
                raise ValueError(f"Duplicate crafting recipe id: {recipe.id}")
            recipes[recipe.id] = recipe
        self._validate_inventory_ids(recipes.values())
        self._recipes = recipes
        self._loaded = True

    def _parse_recipe(self, entry: dict) -> CraftingRecipe:
        if not isinstance(entry, dict):
            raise ValueError("Each crafting recipe must be an object")

        try:
            recipe_id = str(entry["id"])
            inputs_data = entry["inputs"]
            output_data = entry["output"]
        except KeyError as exc:
            raise ValueError("Recipe missing required key") from exc

        inputs = self._parse_ingredients(inputs_data)
        output_item, output_qty = self._parse_output(output_data)
        success_rate = self._parse_success_rate(entry.get("success_rate", 1.0))
        health_cost = int(entry.get("health_cost", 0))
        if health_cost < 0:
            raise ValueError(f"Recipe {recipe_id}: health_cost must be >= 0")
        soul_cost = int(entry.get("soul_cost", SoulCosts.CRAFTING_DEFAULT))
        if soul_cost < 0:
            raise ValueError(f"Recipe {recipe_id}: soul_cost must be >= 0")

        return CraftingRecipe(
            id=recipe_id,
            inputs=inputs,
            output_item=output_item,
            output_qty=output_qty,
            success_rate=success_rate,
            health_cost=health_cost,
            soul_cost=soul_cost,
        )

    def _parse_ingredients(self, inputs_data) -> Tuple[Ingredient, ...]:
        if not isinstance(inputs_data, list) or not inputs_data:
            raise ValueError("Recipe inputs must be a non-empty list")
        ingredients: List[Ingredient] = []
        for raw in inputs_data:
            if not isinstance(raw, dict):
                raise ValueError("Recipe input entries must be objects")
            try:
                item_id = str(raw["item"])
                qty = int(raw.get("qty", 1))
            except KeyError as exc:
                raise ValueError("Recipe input missing 'item' key") from exc
            if qty <= 0:
                raise ValueError("Recipe ingredient qty must be > 0")
            ingredients.append(Ingredient(item_id=item_id, qty=qty))
        return tuple(ingredients)

    def _parse_output(self, output_data) -> Tuple[str, int]:
        if not isinstance(output_data, dict):
            raise ValueError("Recipe output must be an object")
        try:
            item_id = str(output_data["item"])
            qty = int(output_data.get("qty", 1))
        except KeyError as exc:
            raise ValueError("Recipe output missing 'item' key") from exc
        if qty <= 0:
            raise ValueError("Recipe output qty must be > 0")
        return item_id, qty

    @staticmethod
    def _parse_success_rate(value) -> float:
        rate = float(value)
        if rate > 1.0:
            rate = rate / 100.0
        rate = max(0.0, min(1.0, rate))
        return rate

    def all(self) -> Iterable[CraftingRecipe]:
        self.ensure_loaded()
        return self._recipes.values()

    def get(self, recipe_id: str) -> Optional[CraftingRecipe]:
        self.ensure_loaded()
        return self._recipes.get(recipe_id)

    def match_ordered(
        self, ordered_inputs: Tuple[Tuple[str, int], ...]
    ) -> Optional[Tuple[CraftingRecipe, int]]:
        """Return (recipe, multiplier) if ordered_inputs match a recipe."""
        self.ensure_loaded()
        for recipe in self._recipes.values():
            if recipe.matches_ordered(ordered_inputs):
                multiplier = recipe.max_crafts(ordered_inputs)
                if multiplier > 0:
                    return (recipe, multiplier)
        return None

    def reload(self) -> None:
        self._loaded = False
        self._recipes.clear()

    def _validate_inventory_ids(self, recipes: Iterable[CraftingRecipe]) -> None:
        """Ensure every recipe references inventory items that actually exist."""
        available = inventory_items.get_available_items()
        known_ids = set(available.keys())
        missing: List[str] = []

        def _check(item_id: str, context: str) -> None:
            if item_id not in known_ids:
                missing.append(f"{context}:{item_id}")

        for recipe in recipes:
            _check(recipe.output_item, f"{recipe.id}.output")
            for index, ingredient in enumerate(recipe.inputs):
                _check(ingredient.item_id, f"{recipe.id}.input{index+1}")

        if missing:
            details = ", ".join(sorted(set(missing)))
            raise ValueError(f"Crafting recipes reference unknown inventory ids: {details}")


__all__ = [
    "CraftingRecipes",
    "CraftingRecipe",
    "Ingredient",
]
