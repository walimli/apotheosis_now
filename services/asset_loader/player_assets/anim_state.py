from typing import Sequence
import pygame


class AnimState:
    def __init__(self, frames: Sequence[pygame.Surface], frame_time: float = 0.2, *, loop: bool = True):
        self.frames = list(frames)
        self.frame_time = frame_time
        self.loop = loop
        self.timer = 0.0
        self.idx = 0
        self._finished = False

    def reset(self):
        self.timer = 0.0
        self.idx = 0
        self._finished = False

    def update(self, dt: float):
        if self._finished or len(self.frames) <= 1:
            return
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            next_idx = self.idx + 1
            if next_idx >= len(self.frames):
                if self.loop:
                    self.idx = 0
                else:
                    self.idx = len(self.frames) - 1
                    self._finished = True
                    break
            else:
                self.idx = next_idx

    def current(self) -> pygame.Surface:
        return self.frames[self.idx]

    @property
    def is_finished(self) -> bool:
        return self._finished
