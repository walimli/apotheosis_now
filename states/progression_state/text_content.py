from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pygame

from .state_helpers import scale_ui_value


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    if max_width <= 0:
        raise ValueError("max_width must be positive")
    lines: list[str] = []
    paragraphs = text.split("\n")
    for idx, paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            width, _ = font.size(trial)
            if width <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        if idx != len(paragraphs) - 1:
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


class TextContent:
    def __init__(
        self,
        entry: dict,
        font_base_path: Path,
        display_service,
    ) -> None:
        self.id = str(entry["Id"])
        font_name = str(entry["Font"])
        font_path = font_base_path / font_name
        if not font_path.exists():
            raise FileNotFoundError(f"Font file not found: {font_path}")
        color_raw = entry.get("Text_Color")
        if not isinstance(color_raw, (list, tuple)) or len(color_raw) != 3:
            raise ValueError(f"Invalid Text_Color for text entry {self.id}")
        self.color: Tuple[int, int, int] = tuple(int(c) for c in color_raw)  # type: ignore[assignment]
        self.x_offset = int(entry.get("X_offset", 0))
        self.y_offset = int(entry.get("Y_offset", 0))
        self.wrap_width = int(entry.get("Wrap_Width", 0))
        if self.wrap_width <= 0:
            raise ValueError(f"Wrap_Width must be > 0 for text entry {self.id}")

        title_size = scale_ui_value(int(entry.get("Title_Font_Size", entry.get("Font_Size", 24))), display_service)
        body_size = scale_ui_value(int(entry.get("Body_Font_Size", entry.get("Font_Size", 20))), display_service)
        self.x_offset = scale_ui_value(self.x_offset, display_service, minimum=0)
        self.y_offset = scale_ui_value(self.y_offset, display_service, minimum=0)
        self.wrap_width = scale_ui_value(self.wrap_width, display_service)
        self.title_font = display_service.get_scaled_font(str(font_path), title_size)
        self.body_font = display_service.get_scaled_font(str(font_path), body_size)

        self.title_text = str(entry.get("Title", "")).strip()
        body_text = str(entry.get("Body", "")).strip()
        self.title_surface: Optional[pygame.Surface]
        if self.title_text:
            self.title_surface = self.title_font.render(self.title_text, True, self.color)
        else:
            self.title_surface = None

        wrapped = wrap_text(self.body_font, body_text, self.wrap_width) if body_text else []
        self.body_surfaces: list[Optional[pygame.Surface]] = []
        for line in wrapped:
            if not line:
                self.body_surfaces.append(None)
                continue
            surf = self.body_font.render(line, True, self.color)
            self.body_surfaces.append(surf)
        self._body_line_height = self.body_font.get_linesize()

    def draw(self, surface: pygame.Surface, anchor_rect: pygame.Rect) -> None:
        x = anchor_rect.left + self.x_offset
        y = anchor_rect.top + self.y_offset
        if self.title_surface is not None:
            surface.blit(self.title_surface, (x, y))
            y += self.title_surface.get_height() + 12
        for entry in self.body_surfaces:
            if entry is None:
                y += self._body_line_height
                continue
            surface.blit(entry, (x, y))
            y += entry.get_height() + 6


__all__ = ["TextContent", "wrap_text"]
