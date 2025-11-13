from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pygame
from .progression import Progression


class XPCounter:
    """Animated XP counter (22 frames, full->empty)."""

    FRAME_COUNT = 22

    def __init__(self, scale: float = 1.5) -> None:
        sheet_path = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "ui"
            / "counters"
            / "emerald_counter.png"
        )
        sheet = pygame.image.load(str(sheet_path)).convert_alpha()
        width, height = sheet.get_size()

        # Slice vertical strip: FRAME_COUNT segments stacked top->bottom.
        frame_height = max(1, height // self.FRAME_COUNT)
        frames: list[pygame.Surface] = []
        for idx in range(self.FRAME_COUNT):
            rect = pygame.Rect(0, idx * frame_height, width, frame_height)
            frame = sheet.subsurface(rect)
            frames.append(frame)

        self._frame_height = int(round(frame_height * scale))
        self._frame_width = int(round(width * scale))
        if scale != 1.0:
            frames = [
                pygame.transform.smoothscale(f, (self._frame_width, self._frame_height))
                for f in frames
            ]
        self._frames = frames

    @property
    def size(self) -> tuple[int, int]:
        return self._frame_width, self._frame_height

    def draw(
        self,
        surface: pygame.Surface,
        player: Any,
        display,
        *,
        margin_right: int = 16,
        margin_top: int = 16,
    ) -> Optional[pygame.Rect]:
        model = getattr(player, "model", None)
        progression = getattr(model, "progression", None) if model is not None else None
        if progression is None:
            return None

        # Progress represented as xp % XP_PER_EMERALD, clamped to [0, 1].
        try:
            xp_val = int(getattr(progression, "xp", 0))
        except Exception:
            xp_val = 0
        modulo = Progression.XP_PER_EMERALD
        progress = xp_val % modulo
        ratio = max(0.0, min(1.0, progress / float(modulo)))

        # Match health/soul mapping: top frame = full, bottom = empty
        frame_index = int(round((1.0 - ratio) * (self.FRAME_COUNT - 1)))
        frame_index = max(0, min(self.FRAME_COUNT - 1, frame_index))
        frame = self._frames[frame_index]

        left = max(0, int(display.base_width - margin_right - self._frame_width))
        top = max(0, int(margin_top))
        rect = pygame.Rect(left, top, self._frame_width, self._frame_height)
        surface.blit(frame, rect.topleft)
        return rect


__all__ = ["XPCounter"]
