"""Utilities for promoting pygame surfaces into ModernGL textures."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pygame

try:
    import moderngl
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise RuntimeError("Moderngl must be installed to use systems.opengl") from exc

from .context import GLContext


class SurfaceTexture:
    """Wrap a ModernGL texture created from a pygame surface."""

    def __init__(self, surface: pygame.Surface, *, swizzle: bool = True) -> None:
        if surface is None:
            raise ValueError("surface must not be None")
        self._swizzle = bool(swizzle)
        self._texture = self._create_texture(surface)

    @property
    def texture(self) -> moderngl.Texture:
        return self._texture

    def _create_texture(self, surface: pygame.Surface) -> moderngl.Texture:
        ctx = GLContext.ensure()
        width, height = surface.get_size()
        texture = ctx.texture((width, height), 4)
        texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        if self._swizzle:
            texture.swizzle = "BGRA"
        texture.write(surface.get_view("1"))
        return texture

    def update(self, surface: pygame.Surface) -> None:
        if surface is None:
            raise ValueError("surface must not be None")
        width, height = surface.get_size()
        if (width, height) != self._texture.size:
            self._texture.release()
            self._texture = self._create_texture(surface)
        else:
            self._texture.write(surface.get_view("1"))

    def release(self) -> None:
        if self._texture is not None:
            self._texture.release()
            self._texture = None


def load_texture(path: Path, *, convert_alpha: bool = True) -> pygame.Surface:
    """Load an image surface for later promotion to GL."""
    surface = pygame.image.load(str(path))
    if convert_alpha:
        surface = surface.convert_alpha()
    return surface


def surface_from_size(size: Tuple[int, int], color=(0, 0, 0, 0)) -> pygame.Surface:
    surface = pygame.Surface(size, flags=pygame.SRCALPHA)
    surface.fill(color)
    return surface


__all__ = ["SurfaceTexture", "load_texture", "surface_from_size"]
