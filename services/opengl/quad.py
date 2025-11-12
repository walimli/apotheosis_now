"""Shared full-screen quad utilities."""

from __future__ import annotations

from typing import Dict, Tuple

try:
    import moderngl
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise RuntimeError("Moderngl must be installed to use services.opengl") from exc

from .context import GLContext


class QuadRenderer:
    """Create and cache vertex arrays for rendering screen-sized quads."""

    _vao_cache: Dict[Tuple[int, bool, str, Tuple[str, ...]], moderngl.VertexArray] = {}

    @classmethod
    def _vao_key(
        cls,
        program: moderngl.Program,
        textured: bool,
        fmt: str,
        attributes: Tuple[str, ...],
    ) -> Tuple[int, bool, str, Tuple[str, ...]]:
        return id(program), textured, fmt, attributes

    @classmethod
    def vao(
        cls,
        program: moderngl.Program,
        *,
        textured: bool = True,
        fmt: str | None = None,
        attributes: Tuple[str, ...] | None = None,
    ) -> moderngl.VertexArray:
        fmt = fmt or ("2f 2f" if textured else "2f")
        if attributes is None:
            attributes = ("vert", "texcoord") if textured else ("vert",)
        key = cls._vao_key(program, textured, fmt, attributes)
        vao = cls._vao_cache.get(key)
        if vao is not None:
            return vao
        buffer = GLContext.quad_buffer(textured=textured)
        ctx = GLContext.ensure()
        vao = ctx.vertex_array(program, [(buffer, fmt, *attributes)])
        cls._vao_cache[key] = vao
        return vao

    @classmethod
    def render(
        cls,
        program: moderngl.Program,
        *,
        textured: bool = True,
        fmt: str | None = None,
        attributes: Tuple[str, ...] | None = None,
        mode: int | None = None,
    ) -> None:
        vao = cls.vao(program, textured=textured, fmt=fmt, attributes=attributes)
        vao.render(mode=mode or moderngl.TRIANGLE_STRIP)

    @classmethod
    def clear(cls) -> None:
        for vao in cls._vao_cache.values():
            vao.release()
        cls._vao_cache.clear()


__all__ = ["QuadRenderer"]
