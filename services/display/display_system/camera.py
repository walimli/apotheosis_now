import pygame
from constants import TILE_SIZE
# Keep this import as is for now - it's importing from legacy systems
# This will be handled when we integrate the ECS player system


class FollowCamera:
    """Camera with centered deadzone and lerped catch-up toward target.

    - While the player's center remains within a deadzone box (in world pixels)
      centered on the viewport, the camera holds its current origin.
    - When the player exits the deadzone, the camera targets the nearest edge
      that brings the player back to the deadzone and lerps toward it.
    """

    def __init__(self, display, *, deadzone_tiles: int = 2, lerp_rate: float = 12.0):
        self.display = display
        self.scale = 1.0
        self._origin_x = 0.0
        self._origin_y = 0.0
        # Deadzone half-sizes in world pixels (independent of scale)
        self._dz_half_w = max(0, int(deadzone_tiles)) * int(TILE_SIZE)
        self._dz_half_h = max(0, int(deadzone_tiles)) * int(TILE_SIZE)
        # Lerp speed factor (1/s)
        self._lerp_rate = float(lerp_rate)

    def update(self, player: Player, dt: float) -> None:
        # Viewport size in world pixels
        s = float(self.scale) if self.scale > 0 else 1.0
        vw = self.display.base_width / s
        vh = self.display.base_height / s

        # Current viewport center in world coords
        cx = self._origin_x + vw * 0.5
        cy = self._origin_y + vh * 0.5

        # Player center in world coords
        px = float(player.model.x) + float(player.model.w) * 0.5
        py = float(player.model.y) + float(player.model.h) * 0.5

        # Target center clamps player into deadzone bounds
        min_cx = px - self._dz_half_w
        max_cx = px + self._dz_half_w
        min_cy = py - self._dz_half_h
        max_cy = py + self._dz_half_h

        target_cx = cx
        if cx < min_cx:
            target_cx = min_cx
        elif cx > max_cx:
            target_cx = max_cx

        target_cy = cy
        if cy < min_cy:
            target_cy = min_cy
        elif cy > max_cy:
            target_cy = max_cy

        # Convert target center to target origin
        target_ox = target_cx - vw * 0.5
        target_oy = target_cy - vh * 0.5

        # Lerp toward target origin
        alpha = self._lerp_alpha(dt)
        self._origin_x = self._origin_x + (target_ox - self._origin_x) * alpha
        self._origin_y = self._origin_y + (target_oy - self._origin_y) * alpha

    def _lerp_alpha(self, dt: float) -> float:
        try:
            rate = self._lerp_rate
            if rate <= 0 or dt <= 0:
                return 1.0 if rate <= 0 else 0.0
            a = rate * dt
            return 1.0 if a >= 1.0 else a
        except Exception:
            return 1.0

    def world_to_screen(self, pos):
        x, y = pos
        s = self.scale
        return ((x - self._origin_x) * s, (y - self._origin_y) * s)

    @property
    def rect(self):
        """World-space pygame.Rect of the current camera view.

        Width/height are in world pixels (inverse of scale), with top-left at the
        computed origin. Exposed so systems (e.g., world draw/stats) can cull and
        compute visibility consistently.
        """
        vw = int(self.display.base_width / self.scale)
        vh = int(self.display.base_height / self.scale)
        return pygame.Rect(round(self._origin_x), round(self._origin_y), vw, vh)
