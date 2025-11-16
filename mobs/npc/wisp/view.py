from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from systems.mobs.core.base_view import BaseMobView
from .animation import WispAnimationConfig, load_wisp_frames
from .model import WispModel


class WispView(BaseMobView):
    def __init__(
        self,
        model: WispModel,
        frame_size: Tuple[int, int],
        z_index: int,
        animation_config: WispAnimationConfig | None = None,
        scale: float = 1.0,
    ) -> None:
        super().__init__(model, footprint_px=frame_size, z_index=z_index)
        frames, duration = load_wisp_frames(animation_config)
        if not frames:
            raise ValueError("Wisp animation requires at least one frame")
        scale = max(1e-3, float(scale))
        if abs(scale - 1.0) > 1e-6:
            scaled: List[pygame.Surface] = []
            for frame in frames:
                width = max(1, int(round(frame.get_width() * scale)))
                height = max(1, int(round(frame.get_height() * scale)))
                scaled.append(pygame.transform.smoothscale(frame, (width, height)))
            self._frames = scaled
            footprint = (frame_size[0] * scale, frame_size[1] * scale)
            self._foot_w = float(footprint[0])
            self._foot_h = float(footprint[1])
        else:
            self._frames = frames
        self._frame_duration = max(1e-6, float(duration))
        self._timer = 0.0

    def update(self, dt: float) -> None:
        if self.m.is_dead and not self.m.is_moving:
            return
        self._timer += float(dt)

    def _current_frame(self) -> Optional[pygame.Surface]:
        if not self._frames:
            return None
        index = int(self._timer / self._frame_duration) % len(self._frames)
        return self._frames[index]

