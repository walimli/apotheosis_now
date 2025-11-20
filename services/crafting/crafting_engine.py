from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING

from .crafting_assets import CraftingAssets
from .crafting_atlas import CraftingAtlasState
from .crafting_recipes import CraftingRecipe, CraftingRecipes

if TYPE_CHECKING:
    from ecs_core.components import Health, Soul
    from services.inventory.inventory import Inventory


@dataclass(frozen=True)
class CraftOutcome:
    status: str  # "success", "failure", "blocked"
    recipe_id: Optional[str] = None
    output_item: Optional[str] = None
    produced: int = 0
    lost_output: int = 0
    multiplier: int = 0
    consumed: Tuple[Tuple[str, int], ...] = ()
    reason: Optional[str] = None
    health_cost: int = 0
    soul_cost: int = 0

    @property
    def succeeded(self) -> bool:
        return self.status == "success"

    @property
    def failed(self) -> bool:
        return self.status == "failure"


class CraftingEngine:
    """Owns the atlas, cursor, and crafting execution logic."""

    def __init__(
        self,
        assets: CraftingAssets,
        recipes: CraftingRecipes,
        *,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.assets = assets
        self.recipes = recipes
        # Cursor is supplied by the owning system (inventory cursor)
        self.cursor = None
        self.atlas = CraftingAtlasState(assets)
        self._rng = rng or random.Random()
        self._result_lock = False
        self._last_outcome: Optional[CraftOutcome] = None

    # --- State helpers ---
    def busy(self) -> bool:
        return self._result_lock

    def last_outcome(self) -> Optional[CraftOutcome]:
        return self._last_outcome

    def reset(self) -> None:
        self.cursor.clear()
        self.atlas.reset()
        self._result_lock = False
        self._last_outcome = None

    # --- Animation updates ---
    def update(self, dt: float) -> None:
        self.atlas.update(dt)

    def current_frame(self):
        return self.atlas.current_frame()

    # --- Craft execution ---
    def attempt_craft(
        self,
        inventory: Optional["Inventory"],
        health: Optional["Health"],
        soul: Optional["Soul"],
    ) -> CraftOutcome:
        if self._result_lock:
            return CraftOutcome(status="blocked", reason="animation_active")
        if self.cursor.carrying():
            return CraftOutcome(status="blocked", reason="cursor_busy")

        snapshot = self.atlas.storage.snapshot()
        if not snapshot:
            return CraftOutcome(status="blocked", reason="no_ingredients")

        match = self.recipes.match_ordered(snapshot)
        consumed = tuple(snapshot)

        if match is None:
            outcome = CraftOutcome(
                status="failure",
                consumed=consumed,
                reason="no_matching_recipe",
            )
            self._schedule_failure_animation()
            self._last_outcome = outcome
            return outcome

        recipe, multiplier = match
        if multiplier <= 0:
            outcome = CraftOutcome(
                status="failure",
                recipe_id=recipe.id,
                output_item=recipe.output_item,
                consumed=consumed,
                reason="insufficient_quantity",
            )
            self._schedule_failure_animation()
            self._last_outcome = outcome
            return outcome

        roll = self._rng.random()
        if roll > recipe.success_rate:
            outcome = CraftOutcome(
                status="failure",
                recipe_id=recipe.id,
                output_item=recipe.output_item,
                multiplier=multiplier,
                consumed=consumed,
                reason="success_roll_failed",
            )
            self._schedule_failure_animation()
            self._last_outcome = outcome
            return outcome

        soul_cost = recipe.soul_cost * multiplier
        if soul is not None and soul_cost > 0 and not soul.can_spend(soul_cost):
            outcome = CraftOutcome(
                status="blocked",
                recipe_id=recipe.id,
                output_item=recipe.output_item,
                multiplier=multiplier,
                consumed=consumed,
                reason="insufficient_soul",
                soul_cost=soul_cost,
            )
            self._last_outcome = outcome
            return outcome

        self._result_lock = True
        self.atlas.storage.clear()

        total_output = recipe.output_qty * multiplier
        produced = 0
        lost_output = total_output

        if inventory is not None and total_output > 0:
            remainder = inventory.add(recipe.output_item, total_output)
            produced = total_output - remainder
            lost_output = remainder

        health_cost = recipe.health_cost * multiplier
        if health is not None and health_cost > 0:
            health.take_damage(health_cost)
        if soul is not None and soul_cost > 0:
            if not soul.consume(soul_cost):
                # Should not happen due to pre-flight can_spend; treat as exhaustion.
                outcome = CraftOutcome(
                    status="blocked",
                    recipe_id=recipe.id,
                    output_item=recipe.output_item,
                    multiplier=multiplier,
                    consumed=consumed,
                    reason="insufficient_soul",
                    health_cost=health_cost,
                    soul_cost=soul_cost,
                )
                self._schedule_failure_animation()
                self._last_outcome = outcome
                return outcome
        else:
            soul_cost = 0

        outcome = CraftOutcome(
            status="success",
            recipe_id=recipe.id,
            output_item=recipe.output_item,
            produced=produced,
            lost_output=lost_output,
            multiplier=multiplier,
            consumed=consumed,
            health_cost=health_cost,
            soul_cost=soul_cost,
        )
        self._schedule_success_animation()
        self._last_outcome = outcome
        return outcome

    # --- Internal helpers ---
    def _schedule_success_animation(self) -> None:
        self.atlas.animator.play_success(on_complete=self._on_result_complete)

    def _schedule_failure_animation(self) -> None:
        self.atlas.animator.play_failure(on_complete=self._on_result_complete)

    def _on_result_complete(self) -> None:
        self._result_lock = False


__all__ = ["CraftingEngine", "CraftOutcome"]
