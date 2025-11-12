"""ModernGL context bootstrap shared across rendering systems."""
from __future__ import annotations

from array import array
from typing import Optional

try:
    import moderngl
except ModuleNotFoundError as exc:  # pragma: no cover - import guard
    raise RuntimeError("Moderngl must be installed to use systems.opengl") from exc


class GLContext:
    """Singleton-style access to the ModernGL context and quad buffers."""

    _ctx: Optional[moderngl.Context] = None
    _quad_buffer = None
    _quad_buffer_notex = None

    @classmethod
    def ensure(cls) -> moderngl.Context:
        """Return the active ModernGL context, creating it if needed."""
        if cls._ctx is not None:
            return cls._ctx

        cls._ctx = moderngl.create_standalone_context(require=330)
        cls._ctx.enable(moderngl.BLEND)
        cls._ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        cls._init_default_buffers()
        return cls._ctx

    @classmethod
    def get(cls) -> moderngl.Context:
        return cls.ensure()

    @classmethod
    def _init_default_buffers(cls) -> None:
        ctx = cls._ctx
        if ctx is None:
            return
        if cls._quad_buffer is None:
            cls._quad_buffer = ctx.buffer(
                data=array(
                    "f",
                    [
                        -1.0, 1.0, 0.0, 0.0,
                        -1.0, -1.0, 0.0, 1.0,
                        1.0, 1.0, 1.0, 0.0,
                        1.0, -1.0, 1.0, 1.0,
                    ],
                )
            )
        if cls._quad_buffer_notex is None:
            cls._quad_buffer_notex = ctx.buffer(
                data=array(
                    "f",
                    [
                        -1.0, 1.0,
                        -1.0, -1.0,
                        1.0, 1.0,
                        1.0, -1.0,
                    ],
                )
            )

    @classmethod
    def quad_buffer(cls, *, textured: bool = True):
        cls.ensure()
        return cls._quad_buffer if textured else cls._quad_buffer_notex

    @classmethod
    def release(cls) -> None:
        for buf in (cls._quad_buffer, cls._quad_buffer_notex):
            if buf is not None:
                buf.release()
        if cls._ctx is not None:
            cls._ctx.release()
        cls._ctx = None
        cls._quad_buffer = None
        cls._quad_buffer_notex = None


__all__ = ["GLContext"]
