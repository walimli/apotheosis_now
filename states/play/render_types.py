from __future__ import annotations

from typing import NamedTuple, Tuple

import pygame


class RenderPacket(NamedTuple):
    """Minimal data needed to blit a renderable in baseline order."""

    baseline: float
    z: int
    order: Tuple[int, int]
    surface: pygame.Surface
    position: Tuple[int, int]
