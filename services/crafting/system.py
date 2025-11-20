from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable

import pygame

from services.inventory.items import get_icon
from services.inventory.inventory import Inventory
from ecs_core.components import Health, Soul

from .crafting_assets import CraftingAssets
from .crafting_button import CraftingButton
from .crafting_engine import CraftOutcome, CraftingEngine
from .crafting_recipes import CraftingRecipes


@dataclass
class CraftingUIConfig:
    ingredient_slot_size: int = 48
    ingredient_spacing: int = 12
    ingredient_margin: int = 28
    ingredient_bottom_padding: int = 96
    cursor_offset: Tuple[int, int] = (12, 12)
    ingredient_bg: Tuple[int, int, int] = (40, 40, 40)
    ingredient_border: Tuple[int, int, int] = (220, 220, 220)
    ingredient_hover: Tuple[int, int, int] = (255, 215, 160)


class CraftingSystem:
    """Facade that binds button, atlas interaction, and crafting logic."""

    def __init__(
        self,
        inventory: Inventory,
        health: Health,
        soul: Soul,
        *,
        assets: Optional[CraftingAssets] = None,
        recipes: Optional[CraftingRecipes] = None,
        config: Optional[CraftingUIConfig] = None,
    ) -> None:
        self.inventory = inventory
        self.health = health
        self.soul = soul
        self.assets = assets or CraftingAssets()
        self.recipes = recipes or CraftingRecipes()
        self.engine = CraftingEngine(self.assets, self.recipes)
        self.engine.cursor = self.inventory.cursor
        self.button = CraftingButton(self.assets)
        self.config = config or CraftingUIConfig()

        self.active = False
        self._active_listener: Optional[Callable[[bool], None]] = None
        self._surface_size: Tuple[int, int] = (0, 0)
        self._button_surface_size: Tuple[int, int] = (0, 0)
        self._atlas_rect = pygame.Rect(0, 0, 0, 0)
        self._ingredient_rects: List[pygame.Rect] = []
        self._hovered_ingredient: int = -1
        self._mouse_pos: Tuple[int, int] = (0, 0)

        self._font = pygame.font.Font(None, 22)

    # --- Layout ---
    def reposition(
        self,
        base_surface_size: Tuple[int, int],
        *,
        screen_surface_size: Optional[Tuple[int, int]] = None,
    ) -> None:
        base_surface_size = (
            int(base_surface_size[0]),
            int(base_surface_size[1]),
        )
        if screen_surface_size is None:
            screen_surface_size = base_surface_size
        else:
            screen_surface_size = (
                int(screen_surface_size[0]),
                int(screen_surface_size[1]),
            )

        if screen_surface_size != self._button_surface_size:
            self._button_surface_size = screen_surface_size
            self.button.reposition(screen_surface_size)

        if base_surface_size == self._surface_size:
            return
        self._surface_size = base_surface_size

        atlas_frame = self.assets.atlas_loops[1].frames[0]
        rect = atlas_frame.get_rect()
        rect.center = (
            self._surface_size[0] // 2,
            self._surface_size[1] // 2,
        )
        self._atlas_rect = rect

        max_slots = self.engine.atlas.storage.max_unique
        slot_size = self.config.ingredient_slot_size
        spacing = self.config.ingredient_spacing
        total_width = max_slots * slot_size + (max_slots - 1) * spacing
        start_x = rect.centerx - total_width // 2
        y = rect.bottom + self.config.ingredient_margin
        # Clamp ingredient row to remain on-screen within base surface with extra padding
        max_y = (
            self._surface_size[1]
            - slot_size
            - self.config.ingredient_bottom_padding
        )
        if y > max_y:
            y = max_y
        self._ingredient_rects = []
        for i in range(max_slots):
            x = start_x + i * (slot_size + spacing)
            self._ingredient_rects.append(pygame.Rect(x, y, slot_size, slot_size))

    # --- Toggling ---
    def toggle(self) -> None:
        if self.active:
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if self.active:
            return
        self.active = True
        if self._active_listener is not None:
            try:
                self._active_listener(True)
            except Exception:
                pass

    def close(self) -> None:
        if not self.active:
            return
        self._return_cursor_to_inventory()
        self.engine.atlas.storage.refund_to_inventory(self.inventory)
        self.engine.reset()
        self.active = False
        if self._active_listener is not None:
            try:
                self._active_listener(False)
            except Exception:
                pass

    # --- Event handling ---
    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            return self.handle_cursor_move(getattr(event, "pos", None))
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = getattr(event, "pos", None)
            if event.button == 1:
                return self.handle_primary_action(pos)
            if event.button == 3:
                return self.handle_secondary_action(pos)
        return False

    def _update_hover_states(self, pos: Tuple[int, int]) -> None:
        self._hovered_ingredient = -1
        snapshot = self.engine.atlas.storage.snapshot()
        for idx, rect in enumerate(self._ingredient_rects):
            if idx >= len(snapshot):
                break
            if rect.collidepoint(pos):
                self._hovered_ingredient = idx
                break

    # --- Atlas interaction ---
    def _handle_atlas_left_click(self) -> bool:
        cursor = self.engine.cursor
        if cursor.carrying():
            remainder = self.engine.atlas.storage.add_stack(cursor.item_id, cursor.qty)
            if remainder == cursor.qty:
                return False
            if remainder > 0:
                cursor.qty = remainder
            else:
                cursor.clear()
            return True
        outcome = self.engine.attempt_craft(self.inventory, self.health, self.soul)
        return outcome.status != "blocked"

    def _handle_atlas_right_click(self) -> bool:
        cursor = self.engine.cursor
        storage = self.engine.atlas.storage
        if cursor.carrying():
            remainder = storage.add_stack(cursor.item_id, 1)
            if remainder == 0:
                cursor.qty -= 1
                if cursor.qty <= 0:
                    cursor.clear()
                return True
            return False
        if storage.is_empty():
            return False
        index = storage.unique_slots() - 1
        item_id, qty = storage.take_amount(index, 1)
        if item_id is None or qty <= 0:
            return False
        cursor.start_drag(item_id, qty)
        return True

    def _handle_ingredient_click(self, pos: Tuple[int, int], mouse_button: int) -> bool:
        storage_snapshot = self.engine.atlas.storage.snapshot()
        for idx, rect in enumerate(self._ingredient_rects):
            if idx >= len(storage_snapshot):
                break
            if not rect.collidepoint(pos):
                continue
            if mouse_button == 1:
                return self._pickup_ingredient_stack(idx)
            if mouse_button == 3:
                return self._pickup_ingredient_single(idx)
        return False

    def _pickup_ingredient_stack(self, index: int) -> bool:
        cursor = self.engine.cursor
        if cursor.carrying():
            return False
        item_id, qty = self.engine.atlas.storage.remove_stack(index)
        if item_id is None or qty <= 0:
            return False
        cursor.start_drag(item_id, qty)
        return True

    def _pickup_ingredient_single(self, index: int) -> bool:
        cursor = self.engine.cursor
        storage = self.engine.atlas.storage
        if cursor.carrying():
            return False
        item_id, qty = storage.take_amount(index, 1)
        if item_id is None or qty <= 0:
            return False
        cursor.start_drag(item_id, qty)
        return True

    # --- Update & Draw ---
    def update(self, dt: float) -> None:
        self.button.update(dt)
        if self.active:
            self.engine.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Deprecated: Draw only legacy UI path. Button should be drawn at screen scale via HUD.
        if not self.active:
            return

        frame = self.engine.atlas.current_frame()
        if frame is not None:
            frame_rect = frame.get_rect()
            frame_rect.center = self._atlas_rect.center
            surface.blit(frame, frame_rect)

        self._draw_ingredient_slots(surface)

    # --- Split draws for present-at-scale pipeline ---
    def draw_button(self, surface: pygame.Surface) -> None:
        """Draw the crafting toggle button (call at screen scale)."""
        self.button.draw(surface)

    def draw_ui(self, surface: pygame.Surface) -> None:
        """Draw the crafting UI when active (call on base surface)."""
        if not self.active:
            return
        frame = self.engine.atlas.current_frame()
        if frame is not None:
            frame_rect = frame.get_rect()
            frame_rect.center = self._atlas_rect.center
            surface.blit(frame, frame_rect)
        self._draw_ingredient_slots(surface)

    def _draw_ingredient_slots(self, surface: pygame.Surface) -> None:
        snapshot = self.engine.atlas.storage.snapshot()
        for idx, rect in enumerate(self._ingredient_rects):
            if idx >= len(snapshot):
                break
            bg_color = self.config.ingredient_hover if idx == self._hovered_ingredient else self.config.ingredient_bg
            pygame.draw.rect(surface, bg_color, rect)
            pygame.draw.rect(surface, self.config.ingredient_border, rect, 2)

            item_id, qty = snapshot[idx]
            try:
                icon = get_icon(item_id)
                icon_rect = icon.get_rect()
                icon_rect.center = rect.center
                surface.blit(icon, icon_rect)
            except Exception:
                pass

            if qty > 1:
                qty_text = self._font.render(str(qty), True, (255, 255, 255))
                qty_rect = qty_text.get_rect()
                qty_rect.bottomright = rect.bottomright
                surface.blit(qty_text, qty_rect)

    

    # --- Utilities ---
    def _return_cursor_to_inventory(self) -> None:
        cursor = self.engine.cursor
        if not cursor.carrying():
            return
        remainder = self.inventory.add(cursor.item_id, cursor.qty)
        cursor.clear()
        if remainder > 0:
            # Items that cannot return are lost per spec
            pass

    # --- External listeners ---
    def set_active_listener(self, fn: Optional[Callable[[bool], None]]) -> None:
        self._active_listener = fn

    @property
    def atlas_rect(self) -> pygame.Rect:
        return self._atlas_rect.copy()

    @property
    def last_outcome(self) -> Optional[CraftOutcome]:
        return self.engine.last_outcome()

    # --- Input bridge helpers ---
    def handle_cursor_move(self, pos: Optional[Tuple[int, int]]) -> bool:
        if pos is None:
            return False
        ix = int(pos[0])
        iy = int(pos[1])
        self._mouse_pos = (ix, iy)
        if not self.active:
            return False
        self._update_hover_states(self._mouse_pos)
        return True

    def handle_primary_action(self, pos: Optional[Tuple[int, int]]) -> bool:
        if pos is None:
            pos = self._mouse_pos
        if pos is None:
            return False
        ix, iy = int(pos[0]), int(pos[1])
        self._mouse_pos = (ix, iy)
        if not self.active:
            return False
        if self._handle_ingredient_click(self._mouse_pos, 1):
            return True
        if self._atlas_rect.collidepoint(self._mouse_pos):
            return self._handle_atlas_left_click()
        return True

    def handle_secondary_action(self, pos: Optional[Tuple[int, int]]) -> bool:
        if not self.active:
            return False
        if pos is None:
            pos = self._mouse_pos
        if pos is None:
            return False
        ix, iy = int(pos[0]), int(pos[1])
        self._mouse_pos = (ix, iy)
        if self._handle_ingredient_click(self._mouse_pos, 3):
            return True
        if self._atlas_rect.collidepoint(self._mouse_pos):
            return self._handle_atlas_right_click()
        return True


__all__ = ["CraftingSystem", "CraftingUIConfig"]
