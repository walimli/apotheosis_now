from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from .placeables_animator import PlaceableAnimator
from .placeables_asset_loader import PlaceableSpriteBundle
from .placeables_json_reader import PlaceableRecord


Vec2f = Tuple[float, float]


@dataclass
class GhostConfig:
    tint_valid: Tuple[int, int, int, int] = (120, 200, 120, 140)
    tint_invalid: Tuple[int, int, int, int] = (220, 80, 80, 160)


class PlaceableGhost:
    """Render a tinted ghost of a placeable while aiming placement."""

    def __init__(self, config: Optional[GhostConfig] = None) -> None:
        self.config = config or GhostConfig()
        self._bundle: Optional[PlaceableSpriteBundle] = None
        self._record: Optional[PlaceableRecord] = None
        self._animator: Optional[PlaceableAnimator] = None
        self._world_pos: Vec2f = (0.0, 0.0)
        self._scale_override: Optional[float] = None
        self._valid: bool = False
        self._active: bool = False

    def activate(
        self,
        record: PlaceableRecord,
        bundle: PlaceableSpriteBundle,
        world_top_left: Vec2f,
        *,
        scale_override: Optional[float] = None,
    ) -> None:
        self._record = record
        self._bundle = bundle
        self._world_pos = world_top_left
        self._scale_override = scale_override
        self._active = True
        if bundle.is_animated:
            self._animator = PlaceableAnimator(bundle)
        else:
            self._animator = None
        self._valid = False

    def deactivate(self) -> None:
        self._active = False
        self._bundle = None
        self._record = None
        self._animator = None

    def update(self, dt: float) -> None:
        if self._animator:
            self._animator.update(dt)

    def set_valid(self, valid: bool) -> None:
        self._valid = bool(valid)

    def move_to(self, world_top_left: Vec2f) -> None:
        if not self.is_active:
            return
        self._world_pos = world_top_left

    @property
    def is_active(self) -> bool:
        return self._active and self._bundle is not None and self._record is not None

    @property
    def world_position(self) -> Vec2f:
        return self._world_pos

    def draw(self, surface: pygame.Surface, camera) -> None:
        if not self.is_active:
            return
        frame_surface = self._current_frame()
        if frame_surface is None:
            return

        scale = self._scale_override
        if scale is None and self._record is not None:
            scale = float(self._record.scale)
        if scale is None:
            scale = 1.0

        world_w = frame_surface.get_width() * scale
        world_h = frame_surface.get_height() * scale
        if world_w <= 0 or world_h <= 0:
            return

        cam_scale = float(getattr(camera, "scale", 1.0))
        draw_w = max(1, int(round(world_w * cam_scale)))
        draw_h = max(1, int(round(world_h * cam_scale)))

        if abs(scale * cam_scale - 1.0) > 1e-6:
            base_surf = pygame.transform.smoothscale(frame_surface, (draw_w, draw_h))
        else:
            base_surf = frame_surface

        tinted = self._apply_tint(base_surf.copy(), self._valid)
        screen_pos = camera.world_to_screen(self._world_pos)
        surface.blit(tinted, (int(round(screen_pos[0])), int(round(screen_pos[1]))))

    def _current_frame(self) -> Optional[pygame.Surface]:
        if self._animator:
            return self._animator.current_frame()
        if self._bundle:
            return self._bundle.frame()
        return None

    def _apply_tint(self, surface: pygame.Surface, is_valid: bool) -> pygame.Surface:
        tint_color = self.config.tint_valid if is_valid else self.config.tint_invalid
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(tint_color)
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return surface


__all__ = ["PlaceableGhost", "GhostConfig"]
