from __future__ import annotations

from pathlib import Path
from typing import Collection, Dict, Optional, Tuple

import pygame

from .animator import PlayerAnimator
from .image_loader import set_player_asset_root


class PlayerAnimationService:
    """Facade around the legacy PlayerAnimator with inventory awareness."""

    def __init__(
        self,
        *,
        asset_root: Path,
        pick_item_ids: Optional[Collection[str]] = None,
        equip_variants: Optional[Dict[str, str]] = None,
    ) -> None:
        set_player_asset_root(asset_root)
        self._animator = PlayerAnimator()
        base_variants = {
            "pick_wooden_medallion": "pick",
            "sword_wooden_medallion": "sword",
        }
        if equip_variants:
            base_variants.update(
                {key.lower(): value for key, value in equip_variants.items()}
            )
        if pick_item_ids:
            for item_id in pick_item_ids:
                base_variants.setdefault(item_id.lower(), "pick")
        self._equip_variants = {k.lower(): v for k, v in base_variants.items()}
        self._inventory = None
        self._selection_listener = None
        self._fallback_surface: Optional[pygame.Surface] = None
        self._current_variant: Optional[str] = None

    def bind_inventory(self, inventory) -> None:
        """Subscribe to inventory selection updates to track equipped items."""
        if inventory is None:
            return
        if self._inventory is inventory:
            return
        self.unbind_inventory()
        self._inventory = inventory
        self._selection_listener = self._handle_inventory_selection
        inventory.add_selection_listener(self._selection_listener)
        slot = inventory.get_selected_slot()
        self._handle_inventory_selection(  # prime state with current selection
            inventory.get_selected_index()
            if hasattr(inventory, "get_selected_index")
            else 0,
            slot.item_id,
            slot.qty,
        )

    def unbind_inventory(self) -> None:
        if self._inventory is None or self._selection_listener is None:
            self._inventory = None
            self._selection_listener = None
            return
        try:
            self._inventory.remove_selection_listener(self._selection_listener)
        finally:
            self._inventory = None
            self._selection_listener = None

    def set_position(self, position: Tuple[float, float]) -> None:
        self._animator.set_position(position)

    def trigger_action(self, name: str) -> None:
        self._animator.trigger_action(name)

    def play_pick_swing(self) -> None:
        """Play the pick swing animation using the current facing direction."""
        self._play_swing_variant("pick")

    def play_sword_swing(self) -> None:
        """Play the sword swing animation using the current facing direction."""
        self._play_swing_variant("sword")

    def play_interact(self) -> None:
        """Play the interact animation oriented to the current facing."""
        direction = self._animator.last_facing
        suffix = f"_{self._current_variant}" if self._current_variant else ""
        state = f"interact_{direction}{suffix}"
        self._animator.trigger_action(state)

    def get_facing_direction(self) -> str:
        return self._animator.last_facing

    def update(self, dt: float) -> None:
        self._animator.update(dt)

    def current_surface(self) -> Tuple[pygame.Surface, Tuple[int, int]]:
        try:
            frame, _ = self._animator.current_surface_and_offset()
            return frame, self._feet_aligned_offset(frame)
        except RuntimeError:
            return self._fallback_surface_with_offset()

    # --- Internal helpers -------------------------------------------------
    def _handle_inventory_selection(
        self, _slot: int, item_id: Optional[str], qty: int
    ) -> None:
        variant = None
        if item_id and qty > 0:
            variant = self._equip_variants.get(item_id.lower())
        self._current_variant = variant
        self._animator.set_equipped_variant(variant)

    def _fallback_surface_with_offset(self) -> Tuple[pygame.Surface, Tuple[int, int]]:
        if self._fallback_surface is None:
            size = 64
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 200, 255), (size // 2, size // 2), size // 2)
            self._fallback_surface = surf
        offset = self._feet_aligned_offset(self._fallback_surface)
        return self._fallback_surface, offset

    def _play_swing_variant(self, variant: str) -> None:
        direction = self._animator.last_facing
        state = f"swing_{direction}_{variant}"
        self._animator.trigger_action(state)

    @staticmethod
    def _feet_aligned_offset(surface: pygame.Surface) -> Tuple[int, int]:
        width = surface.get_width()
        height = surface.get_height()
        offset_x = int(round(-width * 0.5))
        offset_y = -height
        return (offset_x, offset_y)
