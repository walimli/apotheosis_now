"""Shader compilation helpers built on the shared GL context."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pygame

try:
    import moderngl
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise RuntimeError("Moderngl must be installed to use systems.opengl") from exc

from .context import GLContext
from .quad import QuadRenderer
from .resources import ShaderResourceManager
from .textures import SurfaceTexture

_DEFAULT_VERT = """#version 330

in vec2 vert;
in vec2 texcoord;
out vec2 uv;

void main() {
  uv = texcoord;
  gl_Position = vec4(vert, 0.0, 1.0);
}
"""


@dataclass
class ShaderProgram:
    """Thin wrapper around a moderngl.Program with quad rendering helpers."""

    program: moderngl.Program
    textured: bool = True
    vao_format: str | None = None
    attributes: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        self._temp_textures: list[SurfaceTexture] = []
        self._vao = QuadRenderer.vao(
            self.program,
            textured=self.textured,
            fmt=self.vao_format,
            attributes=self.attributes,
        )

    def render(
        self,
        *,
        uniforms: Optional[Dict[str, Any]] = None,
        target: Optional[moderngl.Framebuffer] = None,
        mode: Optional[int] = None,
    ) -> None:
        framebuffer = target or GLContext.ensure().screen
        framebuffer.use()
        self._apply_uniforms(uniforms or {})
        self._vao.render(mode=mode or moderngl.TRIANGLE_STRIP)
        self._release_temp_textures()

    def _apply_uniforms(self, uniforms: Dict[str, Any]) -> None:
        if not uniforms:
            return
        tex_slot = 0
        for name, value in uniforms.items():
            if name not in self.program:
                continue
            if isinstance(value, pygame.Surface):
                wrapper = SurfaceTexture(value)
                self._temp_textures.append(wrapper)
                texture = wrapper.texture
            elif isinstance(value, SurfaceTexture):
                texture = value.texture
            elif isinstance(value, moderngl.Texture):
                texture = value
            else:
                self.program[name].value = value
                continue
            texture.use(tex_slot)
            self.program[name].value = tex_slot
            tex_slot += 1

    def _release_temp_textures(self) -> None:
        for wrapper in self._temp_textures:
            wrapper.release()
        self._temp_textures.clear()


def compile_shader(
    fragment_source: str,
    *,
    vertex_source: Optional[str] = None,
    textured: bool = True,
    vao_format: str | None = None,
    attributes: Iterable[str] | None = None,
) -> ShaderProgram:
    ctx = GLContext.ensure()
    vert_src = vertex_source or _DEFAULT_VERT
    program = ctx.program(vertex_shader=vert_src, fragment_shader=fragment_source)
    attr_tuple = tuple(attributes) if attributes is not None else None
    return ShaderProgram(program, textured=textured, vao_format=vao_format, attributes=attr_tuple)


def compile_from_files(
    *,
    fragment_path: Path,
    vertex_path: Optional[Path] = None,
    resource_manager: Optional[ShaderResourceManager] = None,
    textured: bool = True,
    vao_format: str | None = None,
    attributes: Iterable[str] | None = None,
) -> ShaderProgram:
    manager = resource_manager or ShaderResourceManager()
    frag_source = manager.shader_source(fragment_path)
    vert_source = manager.shader_source(vertex_path) if vertex_path else None
    return compile_shader(
        frag_source,
        vertex_source=vert_source,
        textured=textured,
        vao_format=vao_format,
        attributes=attributes,
    )


__all__ = ["ShaderProgram", "compile_shader", "compile_from_files"]
