from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pygame

from systems.player.components.inventory_package.ui.hotbar import HotbarUI


class HealthCounter:
    """Animated health counter (31 frames, full->empty)."""

    FRAME_COUNT = 31

    def __init__(self, scale: float = 1.0) -> None:
        sheet_path = (
            Path(__file__).resolve().parents[4]
            / "assets"
            / "ui"
            / "counters"
            / "health_counter.png"
        )
        sheet = pygame.image.load(str(sheet_path)).convert_alpha()
        width, height = sheet.get_size()
        frame_height = max(1, height // self.FRAME_COUNT)
        self._frames: list[pygame.Surface] = []
        for idx in range(self.FRAME_COUNT):
            rect = pygame.Rect(0, idx * frame_height, width, frame_height)
            self._frames.append(sheet.subsurface(rect))
        self._frame_height = int(round(frame_height * scale))
        self._frame_width = int(round(width * scale))
        if scale != 1.0:
            self._frames = [
                pygame.transform.smoothscale(frame, (self._frame_width, self._frame_height))
                for frame in self._frames
            ]

    @property
    def size(self) -> tuple[int, int]:
        return self._frame_width, self._frame_height

    def draw(
        self,
        surface: pygame.Surface,
        player: Any,
        hotbar: HotbarUI,
        display,
        offset: tuple[int, int],
    ) -> Optional[pygame.Rect]:
        model = getattr(player, "model", None)
        health = getattr(model, "health", None) if model is not None else None
        if health is None or health.max_hp <= 0:
            return None

        ratio = max(0.0, min(1.0, health.current_hp / float(health.max_hp)))
        frame_index = int(round((1.0 - ratio) * (self.FRAME_COUNT - 1)))
        frame_index = max(0, min(self.FRAME_COUNT - 1, frame_index))
        frame = self._frames[frame_index]

        hotbar_x, hotbar_y = hotbar.get_position(display.base_width, display.base_height)
        left = int(hotbar_x + offset[0])
        top = int(hotbar_y + offset[1])
        rect = pygame.Rect(left, top, self._frame_width, self._frame_height)
        surface.blit(frame, rect.topleft)
        return rect


__all__ = ["HealthCounter"]
