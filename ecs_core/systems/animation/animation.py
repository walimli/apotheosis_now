import pygame

from ecs_core.components.animation_components import Animation, AnimationState
from ecs_core.components.components import Position


class AnimationSystem:
    """Drives sprite-sheet animations and provides a circle fallback when assets are missing."""

    def __init__(self):
        self.world = None
        self.sheet_cache: dict[str, pygame.Surface] = {}
        self.frame_cache: dict[tuple[str, str], list[pygame.Rect]] = {}

    def _load_sheet(self, path: str) -> pygame.Surface:
        if path not in self.sheet_cache:
            self.sheet_cache[path] = pygame.image.load(path).convert_alpha()
        return self.sheet_cache[path]

    def _build_frames(self, anim: Animation) -> None:
        sheet_path = anim.sheet_path
        if not sheet_path:
            return
        sheet = self._load_sheet(sheet_path)
        key = (sheet_path,)

        for action, frame_count in anim.actions.items():
            cache_key = (sheet_path, action)
            if cache_key in self.frame_cache:
                continue
            row_idx = anim.row_order.index(action)
            frames: list[pygame.Rect] = []
            for i in range(frame_count):
                rect = pygame.Rect(
                    i * anim.frame_w, row_idx * anim.frame_h, anim.frame_w, anim.frame_h
                )
                frames.append(rect)
            self.frame_cache[cache_key] = frames

    def update(self, dt: float) -> None:
        for _eid, (anim, state, _pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            sheet_path = anim.sheet_path
            if sheet_path:
                cache_key = (sheet_path, state.current_action)
                if sheet_path not in self.sheet_cache:
                    self._build_frames(anim)

                frames = self.frame_cache.get(cache_key)
                if not frames:
                    continue

                state.timer += dt
                frame_duration = 1.0 / max(anim.fps, 1e-6)
                while state.timer >= frame_duration:
                    state.timer -= frame_duration
                    state.frame_idx = (state.frame_idx + 1) % len(frames)
            else:
                # Fallback animations do not rely on sprite sheets; keep timer bounded.
                state.timer = 0.0
                state.frame_idx = 0

    def render(self, surface: pygame.Surface, camera_x: int, camera_y: int) -> None:
        for _eid, (anim, state, pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            sheet_path = anim.sheet_path
            if not sheet_path:
                self._render_fallback_circle(surface, pos, camera_x, camera_y, anim)
                continue

            cache_key = (sheet_path, state.current_action)
            sheet = self.sheet_cache.get(sheet_path)
            frames = self.frame_cache.get(cache_key)
            if not sheet or not frames:
                continue

            src_rect = frames[state.frame_idx % len(frames)]
            screen_x = pos.x - camera_x
            screen_y = pos.y - camera_y

            if anim.flip_x_for_left and state.facing_left:
                frame_surface = pygame.transform.flip(
                    sheet.subsurface(src_rect), True, False
                )
                surface.blit(frame_surface, (screen_x, screen_y))
            else:
                surface.blit(sheet, (screen_x, screen_y), src_rect)

    def _render_fallback_circle(
        self,
        surface: pygame.Surface,
        position: Position,
        camera_x: int,
        camera_y: int,
        anim: Animation,
    ) -> None:
        frame_w = getattr(anim, "frame_w", 0) or 0
        frame_h = getattr(anim, "frame_h", 0) or 0
        radius = max(frame_w, frame_h) // 2
        radius = max(4, radius if radius > 0 else 16)
        screen_x = int(position.x - camera_x)
        screen_y = int(position.y - camera_y)
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (screen_x, screen_y),
            int(radius),
        )
