"""Rendering-focused ECS components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

import pygame


@dataclass(frozen=True)
class Camera2DComponent:
    """Viewport state shared across rendering systems."""

    rect: pygame.Rect
    scale: float = 1.0
    scroll: Tuple[float, float] = (0.0, 0.0)


@dataclass(frozen=True)
class VoidVisualComponent:
    """Parameters needed to drive the shader-based void pass."""

    time_offset: float = 0.0
    scroll_speed: Tuple[float, float] = (0.05, 0.02)
    scroll_position: Tuple[float, float] = (0.0, 0.0)
    crt_effect: float = 1.0
    saturation: float = 1.0
    in_void: bool = True
    parallax_factor: float = 0.5
    resources_ready: bool = False


@dataclass(frozen=True)
class TerrainChunkComponent:
    """Placeholder for chunk surface metadata once chunk rendering migrates to ECS."""

    chunk_key: Tuple[int, int]
    surface: Optional[pygame.Surface] = None


@dataclass(frozen=True)
class RenderableEntityComponent:
    """Placeholder describing on-screen renderable entities."""

    entity_id: str
    position: Tuple[float, float]
    sprite_key: Optional[str] = None
    layer: int = 0


__all__ = [
    "Camera2DComponent",
    "VoidVisualComponent",
    "TerrainChunkComponent",
    "RenderableEntityComponent",
]
