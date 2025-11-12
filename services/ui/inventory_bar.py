from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pygame
from ..inventory import Inventory
from ..items import get_icon
from ..interactions import handle_left_click, handle_right_click


class HotbarUI:
    """Visual hotbar component that displays inventory slots at bottom of screen."""

    def __init__(self, inventory: Inventory, lock_state, slot_size: int = 48):
        self.inventory = inventory
        self._lock_state = lock_state
        self.slot_size = slot_size
        self.slots_count = len(inventory.slots)
        self.hovered_slot = -1
        self._mouse_pos: Tuple[int, int] = (0, 0)
        self._lock_hovered = False

        # Visual styling
        self.slot_color = (139, 139, 139)       # Dark gray (used for overlays)
        self.slot_border = (55, 55, 55)         # Very dark gray
        self.selected_color = (255, 255, 255)   # White highlight
        self.hover_color = (200, 200, 200)      # Light gray hover
        self.cursor_offset = (12, 12)

        # Background sprite parameters (legacy art still allocates the leading column for toggles)
        self._base_slot_size = 32  # pixels per box in source sprite
        self._bar_bounds = pygame.Rect(0, 0, 352, 64)
        self._bar_content_origin = pygame.Vector2(16, 16)
        self._bar_content_size = pygame.Vector2(320, 32)

        self.slot_spacing = 0
        self._lock_button_size = self.slot_size
        self._slot_span = self.slots_count * self.slot_size + max(0, self.slots_count - 1) * self.slot_spacing
        gap = self.slot_spacing if self._slot_span > 0 else 0
        self.total_width = self._lock_button_size + gap + self._slot_span
        self.total_height = self.slot_size
        self._bottom_margin = 20

        # Background art
        self._scale = float(self.slot_size) / float(self._base_slot_size)
        self._bar_image = self._load_bar_image(self._scale)
        self._background_size = self._bar_image.get_size()
        self._bg_offset = (
            int(round(self._bar_content_origin.x * self._scale)),
            int(round(self._bar_content_origin.y * self._scale)),
        )

        self._lock_icons = self._load_lock_icons(slot_size)

        # Fonts for quantity display
        self._font = pygame.font.Font(None, max(12, int(slot_size * 0.3)))

    def _load_bar_image(self, scale: float) -> pygame.Surface:
        root = Path(__file__).resolve().parents[5]
        bar_path = root / "assets" / "ui" / "inventory_bar" / "inventory_bar.png"
        base = pygame.image.load(str(bar_path)).convert_alpha()
        if scale == 1.0:
            return base
        target_size = (
            int(round(base.get_width() * scale)),
            int(round(base.get_height() * scale)),
        )
        return pygame.transform.smoothscale(base, target_size)

    def get_position(self, display_width: int, display_height: int) -> Tuple[int, int]:
        """Get hotbar position for bottom-center placement."""
        x = (display_width - self.total_width) // 2
        y = display_height - self._background_size[1] + self._bg_offset[1] - self._bottom_margin
        return x, y

    def get_slot_rect(self, slot_index: int, hotbar_x: int, hotbar_y: int) -> pygame.Rect:
        """Get rect for a specific slot."""
        slot_x = self._slot_origin_x(hotbar_x) + slot_index * (self.slot_size + self.slot_spacing)
        return pygame.Rect(slot_x, hotbar_y, self.slot_size, self.slot_size)

    def get_slot_at_position(self, mouse_x: int, mouse_y: int, hotbar_x: int, hotbar_y: int) -> int:
        """Get which slot the mouse position is over, or -1 if none."""
        for i in range(self.slots_count):
            slot_rect = self.get_slot_rect(i, hotbar_x, hotbar_y)
            if slot_rect.collidepoint(mouse_x, mouse_y):
                return i
        return -1

    def _slot_origin_x(self, hotbar_x: int) -> int:
        offset = self._lock_button_size
        if self.slots_count > 0:
            offset += self.slot_spacing
        return hotbar_x + offset

    def _lock_rect(self, hotbar_x: int, hotbar_y: int) -> pygame.Rect:
        return pygame.Rect(hotbar_x, hotbar_y, self._lock_button_size, self._lock_button_size)

    def _toggle_lock_state(self) -> None:
        if self._lock_state is None:
            return
        self._lock_state.toggle()

    def _lock_icon_surface(self) -> pygame.Surface:
        locked = bool(getattr(self._lock_state, "enabled", False)) if self._lock_state else False
        if locked:
            return self._lock_icons["pressed"]
        if self._lock_hovered:
            return self._lock_icons["hover"]
        return self._lock_icons["default"]

    def _draw_lock_button(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        border_color = self.slot_border
        border_width = 1
        locked = bool(getattr(self._lock_state, "enabled", False)) if self._lock_state else False
        if locked:
            border_color = self.selected_color
            border_width = 2
        elif self._lock_hovered:
            border_color = self.hover_color
        pygame.draw.rect(surface, border_color, rect, border_width)
        icon = self._lock_icon_surface()
        icon_rect = icon.get_rect()
        icon_rect.center = rect.center
        surface.blit(icon, icon_rect)

    def _load_lock_icons(self, target_size: int) -> dict[str, pygame.Surface]:
        root = Path(__file__).resolve().parents[5]
        assets_dir = root / "assets" / "ui" / "icons" / "combat"

        def _load(name: str) -> pygame.Surface:
            path = assets_dir / name
            surface = pygame.image.load(str(path)).convert_alpha()
            if surface.get_width() != target_size or surface.get_height() != target_size:
                surface = pygame.transform.smoothscale(surface, (target_size, target_size))
            return surface

        return {
            "default": _load("combat.png"),
            "hover": _load("combat_hover.png"),
            "pressed": _load("combat_toggle.png"),
        }

    def handle_mouse_motion(self, mouse_pos: Tuple[int, int], hotbar_x: int, hotbar_y: int):
        """Update hover state based on mouse position."""
        self._mouse_pos = mouse_pos
        lock_rect = self._lock_rect(hotbar_x, hotbar_y)
        self._lock_hovered = lock_rect.collidepoint(mouse_pos)
        if self._lock_hovered:
            self.hovered_slot = -1
            return
        self.hovered_slot = self.get_slot_at_position(
            mouse_pos[0], mouse_pos[1], hotbar_x, hotbar_y
        )

    def handle_mouse_button(
        self,
        mouse_pos: Tuple[int, int],
        mouse_button: int,
        hotbar_x: int,
        hotbar_y: int,
    ) -> bool:
        """Handle mouse button interaction with the hotbar."""
        self.handle_mouse_motion(mouse_pos, hotbar_x, hotbar_y)
        slot = self.hovered_slot
        if mouse_button == 1 and self._lock_hovered:
            self._toggle_lock_state()
            return True
        if slot == -1:
            return False

        if mouse_button == 1:
            self.inventory.set_selected_index(slot)
            if not bool(getattr(self._lock_state, "enabled", False)):
                handle_left_click(self.inventory, self.inventory.cursor, slot)
            return True
        if mouse_button == 3:
            return handle_right_click(self.inventory, self.inventory.cursor, slot)
        return False

    def handle_key(self, key: int) -> bool:
        """Handle number key presses for slot selection. Returns True if handled."""
        if pygame.K_1 <= key <= pygame.K_9:
            slot_index = key - pygame.K_1
            if slot_index < self.slots_count:
                self.inventory.set_selected_index(slot_index)
                return True
        return False

    def draw(self, surface: pygame.Surface, display_width: int, display_height: int):
        """Draw the hotbar on the surface."""
        hotbar_x, hotbar_y = self.get_position(display_width, display_height)

        # Draw background bar
        bg_rect = self._bar_image.get_rect()
        bg_rect.topleft = (
            hotbar_x - self._bg_offset[0],
            hotbar_y - self._bg_offset[1],
        )
        surface.blit(self._bar_image, bg_rect)

        lock_rect = self._lock_rect(hotbar_x, hotbar_y)
        self._draw_lock_button(surface, lock_rect)

        # Draw each slot
        for i in range(self.slots_count):
            slot_rect = self.get_slot_rect(i, hotbar_x, hotbar_y)
            slot = self.inventory.slots[i]
            # Determine slot appearance
            if i == self.inventory.selected_index:
                pygame.draw.rect(surface, self.selected_color, slot_rect, 2)
            elif i == self.hovered_slot:
                pygame.draw.rect(surface, self.hover_color, slot_rect, 1)

            # Draw item icon if present
            if not slot.is_empty():
                try:
                    icon = get_icon(slot.item_id)
                    # Center icon in slot
                    icon_rect = icon.get_rect()
                    icon_rect.center = slot_rect.center
                    surface.blit(icon, icon_rect)
                    
                    # Draw quantity if > 1
                    if slot.qty > 1:
                        qty_text = self._font.render(str(slot.qty), True, (255, 255, 255))
                        qty_rect = qty_text.get_rect()
                        qty_rect.bottomright = (slot_rect.right - 2, slot_rect.bottom - 2)
                        surface.blit(qty_text, qty_rect)
                        
                except Exception:
                    # If icon loading fails, just skip drawing it
                    pass

        self._draw_cursor(surface)

    def _draw_cursor(self, surface: pygame.Surface) -> None:
        cursor = self.inventory.cursor
        if not cursor.carrying():
            return

        try:
            icon = get_icon(cursor.item_id)
        except Exception:
            return

        icon_rect = icon.get_rect()
        icon_rect.topleft = (
            self._mouse_pos[0] + self.cursor_offset[0],
            self._mouse_pos[1] + self.cursor_offset[1],
        )
        surface.blit(icon, icon_rect)

        if cursor.qty > 1:
            qty_text = self._font.render(str(cursor.qty), True, (255, 255, 255))
            qty_rect = qty_text.get_rect()
            qty_rect.bottomleft = (icon_rect.right, icon_rect.bottom)
            surface.blit(qty_text, qty_rect)
