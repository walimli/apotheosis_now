"""ModernGL-backed void background renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

import numpy as np
import pygame

from systems.ecs_core import Camera2DComponent, VoidVisualComponent
from services.opengl import (
    GLContext,
    ShaderResourceManager,
    SurfaceTexture,
    compile_from_files,
)


@dataclass
class _FramebufferBundle:
    framebuffer: Any
    size: Tuple[int, int]

    def release(self) -> None:
        if self.framebuffer is not None:
            self.framebuffer.release()
            self.framebuffer = None


class VoidRenderPass:
    """Render a persistent animated void beneath world geometry."""

    def __init__(self) -> None:
        self._resources = ShaderResourceManager()
        self._program = compile_from_files(
            fragment_path=Path("void") / "background.frag",
            vertex_path=Path("void") / "background.vert",
            resource_manager=self._resources,
            textured=False,
            vao_format="2f",
            attributes=("vert",),
        )
        self._framebuffer_bundle: Optional[_FramebufferBundle] = None

    def render(
        self,
        target_surface: pygame.Surface,
        camera: Camera2DComponent,
        params: VoidVisualComponent,
    ) -> None:
        if target_surface is None:
            return
        width, height = target_surface.get_size()
        if width <= 0 or height <= 0:
            return
        framebuffer = self._ensure_framebuffer((width, height))
        uniforms = {
            "time": float(params.time_offset),
            "resolution": (float(width), float(height)),
            "camera_offset": (float(camera.rect.left), float(camera.rect.top)),
            "scroll": tuple(params.scroll_position),
            "crt_effect": float(params.crt_effect),
            "saturation": float(params.saturation),
            "in_void": int(params.in_void),
            "parallax_factor": float(params.parallax_factor),
        }
        framebuffer.framebuffer.clear(0.0, 0.0, 0.0, 1.0)
        self._program.render(uniforms=uniforms, target=framebuffer.framebuffer)
        pixel_bytes = framebuffer.framebuffer.read(components=4, alignment=1)
        array = np.frombuffer(pixel_bytes, dtype=np.uint8)
        array = array.reshape((height, width, 4))
        flipped = np.flipud(array).copy()
        raw_surface = pygame.image.frombuffer(
            flipped.tobytes(), (width, height), "RGBA"
        )
        void_surface = raw_surface.copy()
        target_surface.blit(void_surface, (0, 0))

    def _ensure_framebuffer(self, size: Tuple[int, int]) -> _FramebufferBundle:
        if self._framebuffer_bundle and self._framebuffer_bundle.size == size:
            return self._framebuffer_bundle
        if self._framebuffer_bundle:
            self._framebuffer_bundle.release()
        ctx = GLContext.ensure()
        framebuffer = ctx.simple_framebuffer(size)
        framebuffer.use()
        self._framebuffer_bundle = _FramebufferBundle(
            framebuffer=framebuffer, size=size
        )
        return self._framebuffer_bundle

    def release(self) -> None:
        if self._framebuffer_bundle:
            self._framebuffer_bundle.release()
            self._framebuffer_bundle = None


__all__ = ["VoidRenderPass"]
