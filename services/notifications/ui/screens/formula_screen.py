"""Formula viewer screen showing known recipes and their details."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

import pygame

from services.asset_loader.notification_assets import ButtonImages, NotificationUIAssets
from services.progression.formulas import FormulasLibrary, Recipe
from ..button import ImageButton
from .base import JournalScreen


class FormulaScreenResult(Enum):
    NONE = "none"
    CLOSE = "close"


class FormulaScreen(JournalScreen):
    """Displays player's known formulas with selectable details."""

    TITLE_COLOR = (255, 255, 255)
    LIST_COLOR = (230, 230, 230)
    SELECTED_COLOR = (255, 255, 180)
    DETAILS_COLOR = (255, 255, 255)
    TITLE_FONT_SIZE = 42
    ROW_FONT_SIZE = 28
    DETAILS_TITLE_SIZE = 36
    ROW_SPACING = 12
    TOP_PADDING = 48
    LIST_TOP_OFFSET = 130
    PANEL_RIGHT_MARGIN = 20

    def __init__(self, assets: NotificationUIAssets) -> None:
        super().__init__(assets)
        self._font_path = str(assets.font_path())
        self.panel_surface = assets.panel_surface
        self.panel_rect = self.panel_surface.get_rect()
        self.details_surface = assets.notification_window
        self.details_rect = self.details_surface.get_rect()
        self._surface_size: Tuple[int, int] = (0, 0)

        self.title_font = pygame.font.Font(self._font_path, self.TITLE_FONT_SIZE)
        self.row_font = pygame.font.Font(self._font_path, self.ROW_FONT_SIZE)
        self.details_title_font = pygame.font.Font(
            self._font_path, self.DETAILS_TITLE_SIZE
        )
        self.title_surface = self.title_font.render("Formulas", True, self.TITLE_COLOR)
        self.title_rect = self.title_surface.get_rect()

        self.close_button = self._make_close_button()

        self._library: Optional[FormulasLibrary] = None
        self._list_rows: List[
            Tuple[str, pygame.Surface, pygame.Surface, pygame.Rect]
        ] = []
        self._selected_id: Optional[str] = None

        # Details pre-rendered surfaces
        self._detail_title: Optional[pygame.Surface] = None
        self._detail_lines: List[pygame.Surface] = []
        self._detail_title_pos = pygame.Vector2()
        self._detail_line_positions: List[Tuple[int, int]] = []
        # Empty-state cached rendering for details panel
        self._empty_details_surface: Optional[pygame.Surface] = None
        self._empty_details_pos = pygame.Vector2()

    def _make_close_button(self) -> ImageButton:
        base = self.assets.exit_icon
        hover = self._apply_tint(base, add=50)
        pressed = self._apply_tint(base, sub=60)
        images = ButtonImages(normal=base, hover=hover, pressed=pressed)
        return ImageButton(images)

    @staticmethod
    def _apply_tint(
        surface: pygame.Surface, *, add: int = 0, sub: int = 0
    ) -> pygame.Surface:
        result = surface.copy()
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        if add:
            overlay.fill((add, add, add, 0))
            result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if sub:
            overlay.fill((sub, sub, sub, 0))
            result.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        return result

    # --- External wiring ---
    def attach_library(self, library: FormulasLibrary) -> None:
        self._library = library
        self.refresh()

    def refresh(self) -> None:
        self._rebuild_list()
        # Ensure selection is valid or default to first
        valid_ids = [rid for rid, *_ in self._list_rows]
        if not valid_ids:
            self._selected_id = None
        elif self._selected_id not in valid_ids:
            self._selected_id = valid_ids[0]
        self._rebuild_details()
        # Reposition to lay out new list rects if we know the surface size
        if self._surface_size != (0, 0):
            self.reposition(self._surface_size)

    # --- Internal rebuilds ---
    def _rebuild_list(self) -> None:
        self._list_rows.clear()
        if self._library is None:
            return
        for recipe in self._library.list_known_sorted():
            name = self._library.get_details_payload(recipe.id)["title"]
            normal = self.row_font.render(name, True, self.LIST_COLOR)
            selected = self.row_font.render(name, True, self.SELECTED_COLOR)
            rect = normal.get_rect()
            self._list_rows.append((recipe.id, normal, selected, rect))

    def _rebuild_details(self) -> None:
        self._detail_title = None
        self._detail_lines = []
        self._detail_line_positions = []
        if self._library is None or not self._selected_id:
            return
        payload = self._library.get_details_payload(self._selected_id)
        if payload is None:
            return
        title = str(payload.get("title", ""))
        slots = list(payload.get("slots", []))
        health_cost = int(payload.get("health_cost", 0))
        soul_cost = int(payload.get("soul_cost", 0))

        self._detail_title = self.details_title_font.render(
            title, True, self.DETAILS_COLOR
        )
        self._detail_lines = []
        for line in slots:
            self._detail_lines.append(
                self.row_font.render(line, True, self.DETAILS_COLOR)
            )
        self._detail_lines.append(
            self.row_font.render(
                f"Health Cost: {health_cost}", True, self.DETAILS_COLOR
            )
        )
        self._detail_lines.append(
            self.row_font.render(f"Soul Cost: {soul_cost}", True, self.DETAILS_COLOR)
        )
        self._position_details()

    # --- Layout ---
    def reposition(self, surface_size: Tuple[int, int]) -> None:
        width, height = surface_size
        self._surface_size = surface_size

        # Left panel
        rect = self.panel_surface.get_rect()
        rect.left = 0
        rect.centery = height // 2
        if rect.top < 0:
            rect.top = 0
        if rect.bottom > height:
            rect.bottom = height
        self.panel_rect = rect

        self.title_rect.centerx = rect.centerx
        self.title_rect.top = rect.top + self.TOP_PADDING

        # Position list rows centered within panel
        start_y = rect.top + self.LIST_TOP_OFFSET
        for index, (_, normal, _selected, item_rect) in enumerate(self._list_rows):
            y = start_y + index * (normal.get_height() + self.ROW_SPACING)
            item_rect.centerx = rect.centerx
            item_rect.top = y

        # Details window on the right
        details = self.details_surface.get_rect()
        details.left = rect.right + self.PANEL_RIGHT_MARGIN
        details.centery = rect.centery
        # Clamp to surface bounds
        clamp_area = pygame.Rect(0, 0, width, height)
        details.clamp_ip(clamp_area)
        self.details_rect = details

        self.close_button.set_position(
            (rect.right - self.close_button.rect.width - 20, rect.top + 20)
        )

        self._position_details()
        self._build_empty_details_surface()

    def _position_details(self) -> None:
        if self._detail_title is None:
            return
        self._detail_title_pos.xy = (
            self.details_rect.left + 40,
            self.details_rect.top + 40,
        )
        y = int(self._detail_title_pos.y) + self._detail_title.get_height() + 24
        x = self.details_rect.left + 40
        self._detail_line_positions = []
        for surf in self._detail_lines:
            self._detail_line_positions.append((x, y))
            y += surf.get_height() + self.ROW_SPACING

    def _build_empty_details_surface(self) -> None:
        message = 'Purchase "Formula" attribute to learn more.'
        wrap_width = max(50, self.details_rect.width - 80)
        self._empty_details_surface = self._render_wrapped(
            message, self.row_font, self.DETAILS_COLOR, wrap_width
        )
        self._empty_details_pos.xy = (
            self.details_rect.left + 40,
            self.details_rect.top + 40,
        )

    def _render_wrapped(
        self,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        wrap_width: int,
    ) -> pygame.Surface:
        lines = self._wrap_text(text, font, wrap_width)
        line_height = font.get_linesize()
        height = line_height * len(lines)
        surface = pygame.Surface((wrap_width, height), pygame.SRCALPHA)
        y = 0
        for line in lines:
            rendered = font.render(line, True, color)
            surface.blit(rendered, (0, y))
            y += line_height
        return surface

    def _wrap_text(
        self, text: str, font: pygame.font.Font, wrap_width: int
    ) -> list[str]:
        lines: list[str] = []
        current = ""
        # Single-paragraph wrapping for empty-state message
        for word in text.split(" "):
            candidate = (current + " " + word).strip()
            if not candidate:
                continue
            width, _ = font.size(candidate)
            if width <= wrap_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            lines.append("")
        return lines

    # --- Input ---
    def handle_event(self, event) -> FormulaScreenResult:
        if not self.is_visible():
            return FormulaScreenResult.NONE
        if self.close_button.handle_event(event):
            return FormulaScreenResult.CLOSE
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for rid, _normal, _selected, rect in self._list_rows:
                if rect.collidepoint(pos):
                    if rid != self._selected_id:
                        self._selected_id = rid
                        self._rebuild_details()
                    break
        return FormulaScreenResult.NONE

    def update(self, dt: float) -> None:
        if not self.is_visible():
            return
        self.close_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_visible():
            return
        # Left panel
        surface.blit(self.panel_surface, self.panel_rect)
        surface.blit(self.title_surface, self.title_rect)
        for rid, normal, selected, rect in self._list_rows:
            surf = selected if rid == self._selected_id else normal
            surface.blit(surf, rect)

        # Details window and content
        surface.blit(self.details_surface, self.details_rect)
        if self._list_rows:
            if self._detail_title is not None:
                surface.blit(self._detail_title, self._detail_title_pos)
            for surf, pos in zip(self._detail_lines, self._detail_line_positions):
                surface.blit(surf, pos)
        else:
            if self._empty_details_surface is not None:
                surface.blit(self._empty_details_surface, self._empty_details_pos)

        self.close_button.draw(surface)


__all__ = ["FormulaScreen", "FormulaScreenResult"]
