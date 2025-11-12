"""Shared ModernGL helpers for future shader-based systems."""
from .context import GLContext
from .quad import QuadRenderer
from .shaders import ShaderProgram, compile_shader, compile_from_files
from .textures import SurfaceTexture
from .resources import ShaderResourceManager

__all__ = [
    "GLContext",
    "QuadRenderer",
    "ShaderProgram",
    "compile_shader",
    "compile_from_files",
    "SurfaceTexture",
    "ShaderResourceManager",
]
