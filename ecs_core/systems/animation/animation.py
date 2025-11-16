import pygame
from typing import Optional

from ecs_core.components import Position, Velocity
from ecs_core.components.animation_components import Animation, AnimationState


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

    def _ensure_frames(
        self, anim: Animation, action: str, sheet_path: Optional[str]
    ) -> None:
        if not sheet_path or action not in anim.actions:
            return
        cache_key = (sheet_path, action)
        if cache_key in self.frame_cache:
            return
        row_idx = self._row_index(anim, action)
        if row_idx is None:
            return
        sheet = self._load_sheet(sheet_path)
        frame_count = anim.actions[action]
        frames: list[pygame.Rect] = []
        for i in range(frame_count):
            rect = pygame.Rect(
                i * anim.frame_w, row_idx * anim.frame_h, anim.frame_w, anim.frame_h
            )
            frames.append(rect)
        self.frame_cache[cache_key] = frames

    def _row_index(self, anim: Animation, action: str) -> Optional[int]:
        target = action.strip().lower()
        for idx, label in enumerate(anim.row_order):
            normalized = (label or "").strip().lower()
            if not normalized or normalized == "pass":
                continue
            if normalized == target:
                return idx
        return None

    def _sheet_for_state(self, anim: Animation, state: AnimationState) -> Optional[str]:
        variant_key = getattr(state, "variant", "") or "default"
        if anim.sheet_variants:
            path = anim.sheet_variants.get(variant_key)
            if path:
                return path
        return anim.sheet_path

    def _should_flip(self, anim: Animation, variant: str, facing_left: bool) -> bool:
        if not anim.flip_x_for_left or not facing_left:
            return False
        if anim.flip_variants:
            return variant in anim.flip_variants
        return True

    def update(self, dt: float) -> None:
        for entity_id, (anim, state, _pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            self._drive_state_from_movement(entity_id, anim, state)
            sheet_path = anim.sheet_path
            variant = getattr(state, "variant", "") or "default"
            if anim.sheet_variants:
                sheet_path = self._sheet_for_state(anim, state)

            if sheet_path:
                cache_key = (sheet_path, state.current_action)
                self._ensure_frames(anim, state.current_action, sheet_path)
                frames = self.frame_cache.get(cache_key)
                if not frames:
                    continue

                state.timer += dt
                frame_duration = 1.0 / max(anim.fps, 1e-6)
                while state.timer >= frame_duration:
                    state.timer -= frame_duration
                    state.frame_idx = (state.frame_idx + 1) % len(frames)
            else:
                state.timer = 0.0
                state.frame_idx = 0

    def render(self, surface: pygame.Surface, camera_x: int, camera_y: int) -> None:
        for _eid, (anim, state, pos) in self.world.get_components(
            Animation, AnimationState, Position
        ):
            sheet_path = self._sheet_for_state(anim, state)
            if not sheet_path:
                self._render_fallback_circle(surface, pos, camera_x, camera_y, anim)
                continue

            cache_key = (sheet_path, state.current_action)
            sheet = self.sheet_cache.get(sheet_path)
            frames = self.frame_cache.get(cache_key)
            if not sheet or not frames:
                self._ensure_frames(anim, state.current_action, sheet_path)
                sheet = self.sheet_cache.get(sheet_path)
                frames = self.frame_cache.get(cache_key)
            if not sheet or not frames:
                continue

            src_rect = frames[state.frame_idx % len(frames)]
            base_x = pos.render_x if pos.render_x is not None else float(pos.x)
            base_y = pos.render_y if pos.render_y is not None else float(pos.y)
            screen_x = base_x - camera_x
            screen_y = base_y - camera_y

            variant = getattr(state, "variant", "") or "default"
            if self._should_flip(anim, variant, state.facing_left):
                frame_surface = pygame.transform.flip(
                    sheet.subsurface(src_rect), True, False
                )
                surface.blit(frame_surface, (screen_x, screen_y))
            else:
                surface.blit(sheet, (screen_x, screen_y), src_rect)

    def _drive_state_from_movement(
        self,
        entity_id: int,
        anim: Animation,
        state: AnimationState,
    ) -> None:
        velocity = self.world.get(entity_id, Velocity)
        if velocity:
            speed_sq = velocity.vx * velocity.vx + velocity.vy * velocity.vy
            if speed_sq > 1.0:
                abs_vx = abs(velocity.vx)
                abs_vy = abs(velocity.vy)
                if abs_vx >= abs_vy:
                    state.variant = "side"
                    state.facing_left = velocity.vx < 0
                elif velocity.vy < 0:
                    state.variant = "back"
                    state.facing_left = False
                else:
                    state.variant = "front"
                    state.facing_left = False
                state.current_action = (
                    "walk" if "walk" in anim.actions else state.current_action
                )
                return

        state.current_action = (
            "idle" if "idle" in anim.actions else state.current_action
        )
        if not getattr(state, "variant", None):
            state.variant = "front"

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
        base_x = position.render_x if position.render_x is not None else float(position.x)
        base_y = position.render_y if position.render_y is not None else float(position.y)
        screen_x = int(base_x - camera_x)
        screen_y = int(base_y - camera_y)
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (screen_x, screen_y),
            int(radius),
        )
