import pygame
from ecs_core.components.animation_components import Animation, AnimationState
from ecs_core.components.components import Position


class AnimationSystem:
    def __init__(self):
        self.world = None
        self.sheet_cache = {}  # sheet_path → pygame.Surface
        self.frame_cache = {}  # (sheet_path, action) → list[pygame.Rect]

    def _load_sheet(self, path: str) -> pygame.Surface:
        if path not in self.sheet_cache:
            self.sheet_cache[path] = pygame.image.load(path).convert_alpha()
        return self.sheet_cache[path]

    def _build_frames(self, anim: Animation):
        sheet = self._load_sheet(anim.sheet_path)
        key = (anim.sheet_path,)

        for action, frame_count in anim.actions.items():
            if (key, action) in self.frame_cache:
                continue
            row_idx = anim.row_order.index(action)
            frames = []
            for i in range(frame_count):
                rect = pygame.Rect(
                    i * anim.frame_w, row_idx * anim.frame_h, anim.frame_w, anim.frame_h
                )
                frames.append(rect)
            self.frame_cache[(key, action)] = frames

    def update(self, dt: float):
        for eid, (anim, state, pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            # Build frame cache on first use
            if (anim.sheet_path,) not in self.sheet_cache:
                self._build_frames(anim)

            # Advance timer
            state.timer += dt
            frame_duration = 1.0 / anim.fps
            if state.timer >= frame_duration:
                state.timer -= frame_duration
                frames = self.frame_cache[(anim.sheet_path,), state.current_action]
                state.frame_idx = (state.frame_idx + 1) % len(frames)

    def render(self, surface: pygame.Surface, camera_x: int, camera_y: int):
        for eid, (anim, state, pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            sheet = self.sheet_cache[anim.sheet_path]
            frames = self.frame_cache[(anim.sheet_path,), state.current_action]
            src_rect = frames[state.frame_idx]

            screen_x = pos.x - camera_x
            screen_y = pos.y - camera_y

            if anim.flip_x_for_left and state.facing_left:
                flipped = pygame.transform.flip(sheet.subsurface(src_rect), True, False)
                surface.blit(flipped, (screen_x, screen_y))
            else:
                surface.blit(sheet, (screen_x, screen_y), src_rect)
