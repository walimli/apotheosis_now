from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Tuple

import pygame

from .crafting_assets import AnimationFrames, CraftingAssets


@dataclass
class AtlasIngredient:
    """Represents a unique ingredient stack inside the atlas."""

    item_id: str
    qty: int

    def add(self, amount: int) -> None:
        self.qty = max(0, self.qty + int(amount))

    def remove(self, amount: int) -> int:
        take = max(0, min(self.qty, int(amount)))
        self.qty -= take
        return take

    def is_empty(self) -> bool:
        return self.qty <= 0


class CraftingAtlas:
    """Manages ingredient storage, ordering, and stage notifications."""

    def __init__(
        self,
        max_unique: int = 3,
        stage_listener: Optional[Callable[[int], None]] = None,
    ) -> None:
        self._max_unique = max(1, int(max_unique))
        self._ingredients: List[AtlasIngredient] = []
        self._stage_listener = stage_listener
        self._notify_stage_listener()

    # --- Stage helpers ---
    def unique_slots(self) -> int:
        return len(self._ingredients)

    def stage_index(self) -> int:
        """Return stage index (0-3) representing animation state."""
        count = self.unique_slots()
        return min(max(count, 0), self._max_unique)

    @property
    def max_unique(self) -> int:
        return self._max_unique

    def total_quantity(self) -> int:
        return sum(slot.qty for slot in self._ingredients)

    def is_empty(self) -> bool:
        return not self._ingredients

    # --- Ingredient operations ---
    def can_accept(self, item_id: str) -> bool:
        return self._find_slot(item_id) is not None or len(self._ingredients) < self._max_unique

    def add_stack(self, item_id: str, qty: int) -> int:
        """Add qty of item_id to the atlas, returning any remainder not placed."""
        qty = int(qty)
        if qty <= 0:
            return 0
        prev_stage = self.stage_index()
        slot = self._find_slot(item_id)
        if slot is None:
            if len(self._ingredients) >= self._max_unique:
                return qty
            slot = AtlasIngredient(item_id=item_id, qty=0)
            self._ingredients.append(slot)
        slot.add(qty)
        self._maybe_notify(prev_stage)
        return 0

    def remove_stack(self, index: int) -> Tuple[Optional[str], int]:
        """Remove entire stack at ordered index."""
        prev_stage = self.stage_index()
        slot = self._slot_by_index(index)
        if slot is None:
            return (None, 0)
        self._ingredients.pop(index)
        self._maybe_notify(prev_stage)
        return (slot.item_id, slot.qty)

    def take_amount(self, index: int, amount: int) -> Tuple[Optional[str], int]:
        """Take amount from stack without removing leftovers; returns taken qty."""
        prev_stage = self.stage_index()
        slot = self._slot_by_index(index)
        if slot is None or amount <= 0:
            return (None, 0)
        taken = slot.remove(amount)
        item_id = slot.item_id if taken > 0 else None
        if slot.is_empty():
            self._ingredients.pop(index)
        self._maybe_notify(prev_stage)
        return (item_id, taken)

    def clear(self) -> List[Tuple[str, int]]:
        """Clear atlas and return list of (item_id, qty) that were held."""
        payload = [(slot.item_id, slot.qty) for slot in self._ingredients if slot.qty > 0]
        self._ingredients.clear()
        self._notify_stage_listener()
        return payload

    def refund_to_inventory(self, inventory) -> None:
        """Return all ingredients to the supplied inventory."""
        payload = self.clear()
        for item_id, qty in payload:
            if qty <= 0:
                continue
            remainder = inventory.add(item_id, qty)
            _ = remainder  # Items that do not fit are lost per spec.

    def snapshot(self) -> Tuple[Tuple[str, int], ...]:
        """Return ordered snapshot of ingredients for recipe matching."""
        return tuple((slot.item_id, slot.qty) for slot in self._ingredients if slot.qty > 0)

    def __iter__(self) -> Iterable[AtlasIngredient]:
        return iter(self._ingredients)

    # --- Stage listener management ---
    def set_stage_listener(self, listener: Optional[Callable[[int], None]]) -> None:
        self._stage_listener = listener
        self._notify_stage_listener()

    def _maybe_notify(self, previous_stage: int) -> None:
        if previous_stage != self.stage_index():
            self._notify_stage_listener()

    def _notify_stage_listener(self) -> None:
        if self._stage_listener is None:
            return
        stage = max(0, min(self.stage_index(), self._max_unique))
        self._stage_listener(stage)

    # --- Internal helpers ---
    def _find_slot(self, item_id: str) -> Optional[AtlasIngredient]:
        for slot in self._ingredients:
            if slot.item_id == item_id:
                return slot
        return None

    def _slot_by_index(self, index: int) -> Optional[AtlasIngredient]:
        if index < 0 or index >= len(self._ingredients):
            return None
        return self._ingredients[index]


class _AnimationPlayer:
    """Minimal animation helper for looping and one-shot sequences."""

    def __init__(self) -> None:
        self._frames: List[pygame.Surface] = []
        self._frame_time: float = 0.2
        self._loop: bool = True
        self._index: int = 0
        self._elapsed: float = 0.0
        self._finished: bool = False

    def set_animation(self, animation: AnimationFrames, reset: bool = True) -> None:
        self._frames = list(animation.frames)
        self._frame_time = float(animation.frame_time)
        self._loop = bool(animation.loop)
        if reset or not self._frames:
            self._index = 0
            self._elapsed = 0.0
            self._finished = False
        else:
            self._index = min(self._index, max(len(self._frames) - 1, 0))
        if not self._frames:
            self._finished = True

    def update(self, dt: float) -> None:
        if self._finished or not self._frames:
            return
        self._elapsed += float(dt)
        while self._elapsed >= self._frame_time and not self._finished:
            self._elapsed -= self._frame_time
            self._index += 1
            if self._index >= len(self._frames):
                if self._loop and self._frames:
                    self._index %= len(self._frames)
                else:
                    self._index = max(len(self._frames) - 1, 0)
                    self._finished = True

    def current_frame(self) -> Optional[pygame.Surface]:
        if not self._frames:
            return None
        return self._frames[self._index]

    def reset(self) -> None:
        self._index = 0
        self._elapsed = 0.0
        self._finished = False

    @property
    def finished(self) -> bool:
        return self._finished


class AtlasAnimator:
    """Handles atlas animation loops and success/failure transitions."""

    def __init__(self, assets: CraftingAssets) -> None:
        self._loops = {
            0: assets.atlas_loops[1],
            1: assets.atlas_loops[2],
            2: assets.atlas_loops[3],
            3: assets.atlas_loops[4],
        }
        self._success = assets.success_animation
        self._failure = assets.failure_animation

        self._player = _AnimationPlayer()
        self._current_loop_stage = 0
        self._pending_stage = 0
        self._mode: str = "loop"  # "loop" | "result"
        self._post_result_cb: Optional[Callable[[], None]] = None

        self._switch_to_loop(0, reset=True)

    def set_stage(self, stage: int) -> None:
        stage = max(0, min(stage, 3))
        if self._mode == "result":
            self._pending_stage = stage
            return
        if stage == self._current_loop_stage:
            return
        self._switch_to_loop(stage, reset=True)

    def play_success(self, *, on_complete: Optional[Callable[[], None]] = None) -> None:
        self._play_result(self._success, on_complete=on_complete)

    def play_failure(self, *, on_complete: Optional[Callable[[], None]] = None) -> None:
        self._play_result(self._failure, on_complete=on_complete)

    def _play_result(
        self,
        animation: AnimationFrames,
        *,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        self._mode = "result"
        self._pending_stage = 0  # Always revert to idle loop afterwards
        self._post_result_cb = on_complete
        self._player.set_animation(animation, reset=True)

    def update(self, dt: float) -> None:
        self._player.update(dt)
        if self._mode == "result" and self._player.finished:
            callback = self._post_result_cb
            self._post_result_cb = None
            self._mode = "loop"
            self._switch_to_loop(self._pending_stage, reset=True)
            if callback:
                callback()

    def current_frame(self) -> Optional[pygame.Surface]:
        return self._player.current_frame()

    def reset(self) -> None:
        self._mode = "loop"
        self._pending_stage = 0
        self._post_result_cb = None
        self._switch_to_loop(0, reset=True)

    def _switch_to_loop(self, stage: int, *, reset: bool) -> None:
        stage = max(0, min(stage, 3))
        animation = self._loops.get(stage, self._loops[0])
        self._current_loop_stage = stage
        self._player.set_animation(animation, reset=reset)


class CraftingAtlasState:
    """Convenience wrapper combining storage and animation."""

    def __init__(self, assets: CraftingAssets) -> None:
        self.storage = CraftingAtlas(stage_listener=None)
        self.animator = AtlasAnimator(assets)
        self.storage.set_stage_listener(self.animator.set_stage)

    def update(self, dt: float) -> None:
        self.animator.update(dt)

    def current_frame(self) -> Optional[pygame.Surface]:
        return self.animator.current_frame()

    def reset(self) -> None:
        self.animator.reset()


__all__ = ["CraftingAtlas", "AtlasIngredient", "AtlasAnimator", "CraftingAtlasState"]
