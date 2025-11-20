"""Ghost sprite preview for placement service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from .blueprints import PlacementBlueprint, AnimationSpec

Vec2 = Tuple[float, float]


@dataclass(frozen=True)
class GhostConfig:
    tint_valid: Tuple[int, int, int, int] = (120, 200, 120, 140)
    tint_invalid: Tuple[int, int, int, int] = (220, 80, 80, 160)


class _SpriteBundle:
    def __init__(
        self,
        base_surface: pygame.Surface,
        frames: Optional[Tuple[pygame.Surface, ...]] = None,
        fps: float = 6.0,
    ) -> None:
        self._base = base_surface
        self._frames = frames or (base_surface,)
        self._fps = fps
        self._elapsed = 0.0
        self._frame_index = 0

    def update(self, dt: float) -> None:
        if len(self._frames) <= 1:
            return
        dt = max(0.0, float(dt))
        if dt == 0.0 or self._fps <= 0:
            return
        self._elapsed += dt
        frame_time = 1.0 / self._fps
        while self._elapsed >= frame_time:
            self._elapsed -= frame_time
            self._frame_index = (self._frame_index + 1) % len(self._frames)

    def current_frame(self) -> pygame.Surface:
        return self._frames[self._frame_index]


class PlacementSpriteLibrary:
    """Loads and caches sprite bundles for placement previews."""

    def __init__(self) -> None:
        self._cache: dict[str, _SpriteBundle] = {}

    def load(self, blueprint: PlacementBlueprint) -> _SpriteBundle:
        cache_key = blueprint.sprite_path
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        base_surface = pygame.image.load(blueprint.sprite_path).convert_alpha()
        frames: Optional[Tuple[pygame.Surface, ...]] = None
        fps = 6.0
        if blueprint.animation is not None:
            frames = self._load_frames(base_surface, blueprint.animation)
            fps = blueprint.animation.fps
        bundle = _SpriteBundle(base_surface, frames, fps)
        self._cache[cache_key] = bundle
        return bundle

    def _load_frames(
        self,
        sheet_surface: pygame.Surface,
        spec: AnimationSpec,
    ) -> Tuple[pygame.Surface, ...]:
        frames: list[pygame.Surface] = []
        width = spec.frame_width
        height = spec.frame_height
        for row in range(spec.rows):
            for col in range(spec.columns):
                rect = pygame.Rect(col * width, row * height, width, height)
                frames.append(sheet_surface.subsurface(rect).copy())
        return tuple(frames)


class PlacementGhost:
    """Render a tinted placement ghost at the candidate tile."""

    def __init__(
        self,
        sprite_library: Optional[PlacementSpriteLibrary] = None,
        config: Optional[GhostConfig] = None,
    ) -> None:
        self._library = sprite_library or PlacementSpriteLibrary()
        self.config = config or GhostConfig()
        self._bundle: Optional[_SpriteBundle] = None
        self._blueprint: Optional[PlacementBlueprint] = None
        self._world_pos: Vec2 = (0.0, 0.0)
        self._valid: bool = False
        self._active: bool = False

    def activate(self, blueprint: PlacementBlueprint, world_position: Vec2) -> None:
        self._blueprint = blueprint
        self._bundle = self._library.load(blueprint)
        self._world_pos = world_position
        self._valid = False
        self._active = True

    def deactivate(self) -> None:
        self._active = False
        self._bundle = None
        self._blueprint = None

    def move_to(self, world_position: Vec2) -> None:
        if not self.is_active:
            return
        self._world_pos = world_position

    def set_valid(self, valid: bool) -> None:
        self._valid = bool(valid)

    def update(self, dt: float) -> None:
        if self._bundle:
            self._bundle.update(dt)

    def draw(self, surface: pygame.Surface, camera) -> None:
        if not self.is_active or not self._bundle or not self._blueprint:
            return
        frame = self._bundle.current_frame()
        scale = float(self._blueprint.scale or 1.0)
        width = max(1, int(round(frame.get_width() * scale)))
        height = max(1, int(round(frame.get_height() * scale)))

        if width <= 0 or height <= 0:
            return

        if scale != 1.0:
            frame_surface = pygame.transform.smoothscale(frame, (width, height))
        else:
            frame_surface = frame

        tinted = self._apply_tint(frame_surface.copy())
        draw_pos = self._resolve_draw_position(width, height)
        screen_pos = self._world_to_screen(camera, draw_pos)
        surface.blit(tinted, (int(round(screen_pos[0])), int(round(screen_pos[1]))))

    @property
    def is_active(self) -> bool:
        return self._active and self._bundle is not None and self._blueprint is not None

    def _resolve_draw_position(self, width: int, height: int) -> Vec2:
        if not self._blueprint:
            return self._world_pos
        anchor_x, anchor_y = self._blueprint.anchor
        offset_x, offset_y = self._blueprint.offset
        x = self._world_pos[0] - width * anchor_x + offset_x
        y = self._world_pos[1] - height * anchor_y + offset_y
        return (x, y)

    def _apply_tint(self, surface: pygame.Surface) -> pygame.Surface:
        tint = self.config.tint_valid if self._valid else self.config.tint_invalid
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(tint)
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return surface

    def _world_to_screen(self, camera, world_pos: Vec2) -> Vec2:
        if camera is None:
            return world_pos
        if hasattr(camera, "world_to_screen"):
            return camera.world_to_screen(world_pos)
        rect = getattr(camera, "rect", pygame.Rect(0, 0, 0, 0))
        scale = float(getattr(camera, "scale", 1.0))
        return (
            (world_pos[0] - rect.left) * scale,
            (world_pos[1] - rect.top) * scale,
        )


__all__ = ["PlacementGhost", "PlacementSpriteLibrary", "GhostConfig"]
