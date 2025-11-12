"""Centralized shader/textures resource loading with caching."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pygame

from .textures import load_texture


class ShaderResourceManager:
    """Resolve shader and texture assets relative to the project tree."""

    def __init__(self, *, assets_root: Optional[Path] = None) -> None:
        base = assets_root or Path(__file__).resolve().parents[2] / "assets"
        self.shader_root = base / "shaders"
        self.texture_root = base / "textures"
        self._text_cache: Dict[Path, str] = {}
        self._surface_cache: Dict[Path, pygame.Surface] = {}

    def shader_source(self, relative: str | Path) -> str:
        path = (self.shader_root / Path(relative)).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Shader file not found: {path}")
        cached = self._text_cache.get(path)
        if cached is not None:
            return cached
        text = path.read_text(encoding="utf-8")
        self._text_cache[path] = text
        return text

    def surface(self, relative: str | Path, *, convert_alpha: bool = True) -> pygame.Surface:
        path = (self.texture_root / Path(relative)).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Texture file not found: {path}")
        cached = self._surface_cache.get(path)
        if cached is not None:
            return cached
        surface = load_texture(path, convert_alpha=convert_alpha)
        self._surface_cache[path] = surface
        return surface

    def clear(self) -> None:
        self._text_cache.clear()
        self._surface_cache.clear()


__all__ = ["ShaderResourceManager"]
