from __future__ import annotations

from typing import Optional, Tuple

import pygame

from states.play_state.render_types import RenderPacket


class BaseMobView:
    """Shared sprite anchoring + baseline helpers for mob views."""

    def __init__(
        self,
        model,
        *,
        footprint_px: Tuple[int, int] = (64, 64),
        z_index: int = 0,
        sprite_offset_px: float = 0.0,
    ) -> None:
        self.m = model
        self._foot_w = float(footprint_px[0])
        self._foot_h = float(footprint_px[1])
        self._z_index = int(z_index)
        self._sprite_offset_px = float(sprite_offset_px)
        self.scale_with_camera = True
        # Cache for camera-scaled frames keyed by (surface, scale)
        self._scale_cache: dict[tuple[pygame.Surface, float], pygame.Surface] = {}

    @property
    def footprint_px(self) -> Tuple[float, float]:
        return (self._foot_w, self._foot_h)


    # --- Lifecycle ---
    def update(self, dt: float) -> None:
        """Allow subclasses to update animations. Default noop."""
        return None

    # --- Rendering ---
    def render_packet(self, camera=None) -> Optional[RenderPacket]:
        frame = self._current_frame()
        if frame is None:
            return None

        scale = 1.0
        if camera is not None:
            scale = float(getattr(camera, "scale", 1.0))

        draw_surface = frame
        if self.scale_with_camera and abs(scale - 1.0) > 1e-6:
            fw = int(round(frame.get_width() * scale))
            fh = int(round(frame.get_height() * scale))
            if fw <= 0 or fh <= 0:
                return None
            key = (frame, scale)
            cached = self._scale_cache.get(key)
            if cached is None or cached.get_width() != fw or cached.get_height() != fh:
                cached = pygame.transform.scale(frame, (fw, fh))
                self._scale_cache[key] = cached
            draw_surface = cached
            fw, fh = draw_surface.get_size()
        else:
            fw, fh = frame.get_width(), frame.get_height()

        world_x = float(getattr(self.m, "x", 0.0))
        world_y = float(getattr(self.m, "y", 0.0))
        if camera is not None and hasattr(camera, "world_to_screen"):
            screen_x, screen_y = camera.world_to_screen((world_x, world_y))
        else:
            screen_x, screen_y = world_x, world_y

        tile_w = int(round(self._foot_w * scale))
        tile_h = int(round(self._foot_h * scale))
        offset_x = (tile_w - fw) // 2
        offset_y = tile_h - fh - int(round(self._sprite_offset_px * scale))

        baseline = float(world_y + self._foot_h)
        order = int(getattr(self.m, "id", 0))
        pos = (int(round(screen_x + offset_x)), int(round(screen_y + offset_y)))
        return RenderPacket(baseline, self._z_index, order, draw_surface, pos)

    def draw(self, surface: pygame.Surface, camera=None) -> None:
        packet = self.render_packet(camera)
        if packet is None:
            return
        surface.blit(packet.surface, packet.position)

    # --- Hooks ---
    def _current_frame(self) -> Optional[pygame.Surface]:
        raise NotImplementedError


