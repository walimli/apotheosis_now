import os
import pygame
from .defaults import BASE_WIDTH, BASE_HEIGHT, BORDERLESS_DEFAULT
from .camera import FollowCamera


class DisplayService:
    """Manage window, base surface, and present-time scaling.

    - States render to a logical base Surface; present scales by a fixed 2x
      using nearest-neighbor and centers with letterboxing.
    - For renderer-driven scaling safety, SDL's scale quality hint is set to
      nearest in main.py before importing pygame:
        os.environ['SDL_RENDER_SCALE_QUALITY'] = '0'
    - HUD draws after present at screen scale; this class does not flip.
    """

    def __init__(
        self,
        initial_width: int = BASE_WIDTH,
        initial_height: int = BASE_HEIGHT,
        borderless: bool = BORDERLESS_DEFAULT,
    ):
        # Track desired window mode
        self._borderless = bool(borderless)
        # Last known windowed size (used when leaving borderless)
        self._windowed_width = int(initial_width)
        self._windowed_height = int(initial_height)
        # Screen is the actual window size; base is the logical render surface size
        if self._borderless:
            # Use primary desktop resolution for borderless window
            # Requires pygame 2.x: get_desktop_sizes returns a list of (w, h)
            dw, dh = pygame.display.get_desktop_sizes()[0]
            self.screen_width = int(dw)
            self.screen_height = int(dh)
        else:
            self.screen_width = int(initial_width)
            self.screen_height = int(initial_height)
        # Fixed present-time pixel scale (2x) for crisp pixels
        self._pixel_scale = 2
        # Base surface logical size derived from screen and fixed pixel scale
        self.base_width = max(1, self.screen_width // self._pixel_scale)
        self.base_height = max(1, self.screen_height // self._pixel_scale)
        self._create_screen()
        self._create_base_surface()
        self._camera = FollowCamera(self)

    def _create_screen(self):
        if self._borderless:
            # Ensure window spawns at origin on primary monitor
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
            flags = pygame.NOFRAME
        else:
            flags = pygame.RESIZABLE
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), flags)

    def _create_base_surface(self):
        self.base_surface = pygame.Surface((self.base_width, self.base_height))

    def handle_resize(self, event):
        """Handle VIDEORESIZE event."""
        if self._borderless:
            # Ignore resizes while borderless; the window size follows desktop
            return
        new_width, new_height = event.size
        self.screen_width = int(new_width)
        self.screen_height = int(new_height)
        # Track last windowed size for toggling back from borderless
        self._windowed_width = self.screen_width
        self._windowed_height = self.screen_height
        # Update screen and recompute logical base surface for fixed 2x present scale
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), pygame.RESIZABLE
        )
        self._recompute_base_for_screen()

    def get_base_surface(self):
        """Get the base surface for states to render to."""
        return self.base_surface

    def update_camera(self, target_pos, dt: float, target_size=None) -> None:
        """Update the follow camera to track the supplied target."""
        if self._camera is None:
            self._camera = FollowCamera(self)
        self._camera.update(target_pos, dt, target_size)

    def get_camera_rect(self) -> pygame.Rect:
        """Return the current camera rect in world coordinates."""
        if self._camera is None:
            self._camera = FollowCamera(self)
        return self._camera.rect

    def get_camera_scale(self) -> float:
        if self._camera is None:
            self._camera = FollowCamera(self)
        return float(getattr(self._camera, "scale", 1.0))

    def world_to_screen(self, pos):
        if self._camera is None:
            self._camera = FollowCamera(self)
        return self._camera.world_to_screen(pos)

    def _ensure_screen(self):
        if self.screen is None or self.screen.get_size() != (
            self.screen_width,
            self.screen_height,
        ):
            self._create_screen()

    def get_scaled_font(self, font_path, base_size):
        """Get a font with base size (no scaling, for base surface)."""
        return pygame.font.Font(font_path, base_size)

    def render(self):
        """Present the base surface scaled by fixed 2x, centered (letterboxed).

        Note: This method does NOT flip the display. Callers should draw any
        overlays (HUD) after this and then call pygame.display.flip().
        """
        self._ensure_screen()
        k = int(self._pixel_scale)  # fixed 2
        scaled_w = self.base_width * k
        scaled_h = self.base_height * k
        # Nearest-neighbor scale of the composed frame
        scaled_surface = (
            self.base_surface
            if k == 1
            else pygame.transform.scale(self.base_surface, (scaled_w, scaled_h))
        )
        # Center with letterbox bars (may have 1px bars when screen is odd-sized)
        offset_x = (self.screen_width - scaled_w) // 2
        offset_y = (self.screen_height - scaled_h) // 2
        # Save present params for input mapping
        self._present_offset = (offset_x, offset_y)
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled_surface, (offset_x, offset_y))

    def get_present_params(self) -> tuple[int, int, int]:
        """Return fresh (pixel_scale, offset_x, offset_y) for input mapping.

        Always computes offsets from current sizes so mapping is correct even
        between resize and the next render.
        """
        k = int(self._pixel_scale)
        scaled_w = self.base_width * k
        scaled_h = self.base_height * k
        offset_x = (self.screen_width - scaled_w) // 2
        offset_y = (self.screen_height - scaled_h) // 2
        return k, int(offset_x), int(offset_y)

    def _recompute_base_for_screen(self) -> None:
        """Recompute base surface size from current screen size for fixed 2x present scale."""
        sw, sh = max(1, int(self.screen_width)), max(1, int(self.screen_height))
        p = max(1, int(self._pixel_scale))  # fixed 2x
        new_base_w = max(1, sw // p)
        new_base_h = max(1, sh // p)
        if new_base_w != self.base_width or new_base_h != self.base_height:
            self.base_width = new_base_w
            self.base_height = new_base_h
            self._create_base_surface()
        elif not hasattr(self, "base_surface"):
            self._create_base_surface()

    def set_borderless(self, active: bool) -> None:
        """Enable/disable borderless mode at runtime.

        When enabling, the window is resized to the primary desktop resolution
        with no frame. When disabling, the window returns to the last
        windowed size tracked by the display service.
        """
        active = bool(active)
        if active == self._borderless:
            return
        self._borderless = active
        if self._borderless:
            dw, dh = pygame.display.get_desktop_sizes()[0]
            self.screen_width = int(dw)
            self.screen_height = int(dh)
        else:
            self.screen_width = int(self._windowed_width)
            self.screen_height = int(self._windowed_height)
        self._create_screen()
        self._recompute_base_for_screen()
