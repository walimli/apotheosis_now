# time_system/time_display.py
import pygame
from typing import Optional, Tuple
from .game_clock import GameClock
from .time_events import TimePhase

# Try to import UI helpers, fall back gracefully
try:
    from ui import load_font, load_mono_font, blit_text
except ImportError:
    # Fallback implementations
    def load_font(size: int) -> pygame.font.Font:
        return pygame.font.SysFont(None, size)

    def load_mono_font(size: int) -> pygame.font.Font:
        for name in ["Consolas", "Courier New", "DejaVu Sans Mono", "Menlo"]:
            font = pygame.font.SysFont(name, size)
            if font:
                return font
        return pygame.font.SysFont(None, size)

    def blit_text(surface, text, font, pos, color=(255, 255, 255), shadow=False):
        if shadow:
            shadow_img = font.render(text, True, (0, 0, 0))
            surface.blit(shadow_img, (pos[0] + 2, pos[1] + 2))
        img = font.render(text, True, color)
        surface.blit(img, pos)


class TimeDisplay:
    """Enhanced time display that shows both real and game time."""

    def __init__(
        self,
        clock: GameClock,
        pos: Tuple[int, int] = (30, 30),
        show_real_time: bool = False,
        use_12_hour: bool = True,
    ):
        self.clock = clock
        self.pos = pos
        self.show_real_time = show_real_time
        self.use_12_hour = use_12_hour

        # Fonts
        self._label_font = load_font(24)
        self._time_font = load_mono_font(36)
        self._phase_font = load_font(18)
        self._small_font = load_font(16)

        # Layout
        self._pad_x = 18
        self._pad_y = 12

        # Visual settings
        self.show_phase = True
        self.show_day_number = True

    def set_position(self, pos: Tuple[int, int]) -> None:
        """Update display position."""
        self.pos = pos

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the time display."""
        if not screen:
            return

        state = self.clock.get_current_state()

        # Prepare text elements
        elements = self._prepare_text_elements(state)

        # Calculate background size
        bg_size = self._calculate_background_size(elements)

        # Draw background
        self._draw_background(screen, bg_size)

        # Draw text elements
        self._draw_text_elements(screen, elements)

    def _prepare_text_elements(self, state) -> dict:
        """Prepare all text elements for rendering."""
        elements = {}

        # Main game time
        game_time_str = self.clock.get_formatted_time(self.use_12_hour)
        elements["game_time"] = {
            "text": game_time_str,
            "font": self._time_font,
            "color": (245, 245, 245),
        }

        # Day number
        if self.show_day_number:
            elements["day"] = {
                "text": f"Day {state.game_day}",
                "font": self._label_font,
                "color": (200, 200, 200),
            }

        # Phase description
        if self.show_phase:
            phase_color = self._get_phase_color(state.phase)
            elements["phase"] = {
                "text": state.phase.value.capitalize(),
                "font": self._phase_font,
                "color": phase_color,
            }

        # Real time (if enabled)
        if self.show_real_time:
            real_minutes = int(state.real_elapsed // 60)
            real_seconds = int(state.real_elapsed % 60)
            elements["real_time"] = {
                "text": f"Real: {real_minutes:02d}:{real_seconds:02d}",
                "font": self._small_font,
                "color": (160, 160, 160),
            }

        return elements

    def _get_phase_color(self, phase: TimePhase) -> Tuple[int, int, int]:
        """Get color for phase text based on current phase."""
        colors = {
            TimePhase.DAWN: (255, 200, 150),  # Warm orange
            TimePhase.DAY: (255, 255, 200),  # Bright yellow
            TimePhase.DUSK: (255, 150, 100),  # Orange/red
            TimePhase.NIGHT: (150, 180, 255),  # Cool blue
        }
        return colors.get(phase, (255, 255, 255))

    def _calculate_background_size(self, elements: dict) -> Tuple[int, int]:
        """Calculate required background size."""
        max_width = 0
        total_height = self._pad_y * 2

        # Calculate dimensions for each element
        for key, element in elements.items():
            if key == "debug" and isinstance(element["text"], list):
                # Handle debug text lines
                for line in element["text"]:
                    text_surface = element["font"].render(line, True, element["color"])
                    max_width = max(max_width, text_surface.get_width())
                    total_height += text_surface.get_height() + 2
            else:
                text_surface = element["font"].render(
                    element["text"], True, element["color"]
                )
                max_width = max(max_width, text_surface.get_width())
                total_height += text_surface.get_height() + 4

        return (max_width + self._pad_x * 2, total_height)

    def _draw_background(self, screen: pygame.Surface, size: Tuple[int, int]) -> None:
        """Draw the background card."""
        bg_rect = pygame.Rect(self.pos[0], self.pos[1], size[0], size[1])

        # Main background
        pygame.draw.rect(screen, (25, 25, 25), bg_rect, border_radius=8)

        # Border
        pygame.draw.rect(screen, (60, 60, 60), bg_rect, width=1, border_radius=8)

    def _draw_text_elements(self, screen: pygame.Surface, elements: dict) -> None:
        """Draw all text elements."""
        current_y = self.pos[1] + self._pad_y

        # Draw in specific order
        draw_order = ["day", "game_time", "phase", "real_time", "debug"]

        for key in draw_order:
            if key not in elements:
                continue

            element = elements[key]

            if key == "debug" and isinstance(element["text"], list):
                # Handle debug lines
                for line in element["text"]:
                    text_pos = (self.pos[0] + self._pad_x, current_y)
                    blit_text(
                        screen,
                        line,
                        element["font"],
                        text_pos,
                        element["color"],
                        shadow=True,
                    )
                    current_y += element["font"].get_height() + 2
            else:
                # Handle regular text
                text_pos = (self.pos[0] + self._pad_x, current_y)
                blit_text(
                    screen,
                    element["text"],
                    element["font"],
                    text_pos,
                    element["color"],
                    shadow=True,
                )
                current_y += element["font"].get_height() + 4


class GameTimeOverlay:
    """Simplified overlay that integrates with existing TimerOverlay style."""

    def __init__(
        self,
        clock: GameClock,
        label: str = "Game Time",
        pos: Tuple[int, int] = (30, 30),
        use_12_hour: bool = True,
    ):
        self.clock = clock
        self.label = label
        self.pos = pos
        self.use_12_hour = use_12_hour

        # Fonts (matching TimerOverlay style)
        self._label_font = load_font(36)
        self._digit_font = load_mono_font(64)
        self._pad_x = 18
        self._pad_y = 10

    def draw(self, screen: pygame.Surface) -> None:
        """Draw simple time overlay matching TimerOverlay style."""
        if not screen:
            return

        time_str = self.clock.get_formatted_time(self.use_12_hour)
        state = self.clock.get_current_state()
        day_str = f"Day {state.game_day}"

        day_img = self._label_font.render(day_str, True, (200, 200, 200))
        label_img = self._label_font.render(self.label, True, (220, 220, 220))
        digits_img = self._digit_font.render(time_str, True, (245, 245, 245))

        block_w = (
            max(day_img.get_width(), label_img.get_width(), digits_img.get_width())
            + self._pad_x * 2
        )
        block_h = (
            day_img.get_height()
            + label_img.get_height()
            + digits_img.get_height()
            + self._pad_y * 4
        )

        bg_rect = pygame.Rect(self.pos[0], self.pos[1], block_w, block_h)
        pygame.draw.rect(screen, (25, 25, 25), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), bg_rect, width=1, border_radius=8)

        day_pos = (self.pos[0] + self._pad_x, self.pos[1] + self._pad_y)
        label_pos = (self.pos[0] + self._pad_x, day_pos[1] + day_img.get_height() + 6)
        digits_pos = (
            self.pos[0] + self._pad_x,
            label_pos[1] + label_img.get_height() + 6,
        )

        blit_text(
            screen, day_str, self._label_font, day_pos, (200, 200, 200), shadow=True
        )
        blit_text(
            screen,
            self.label,
            self._label_font,
            label_pos,
            (220, 220, 220),
            shadow=True,
        )
        blit_text(
            screen, time_str, self._digit_font, digits_pos, (245, 245, 245), shadow=True
        )


class CombinedTimeOverlay:
    """Combined overlay showing both real time and game time."""

    def __init__(
        self,
        clock: GameClock,
        real_elapsed: float,
        pos: Tuple[int, int] = (30, 30),
        use_12_hour: bool = True,
    ):
        self.clock = clock
        self.real_elapsed = real_elapsed  # Reference to external real time
        self.pos = pos
        self.use_12_hour = use_12_hour

        # Fonts
        self._label_font = load_font(24)
        self._time_font = load_mono_font(36)
        self._pad_x = 18
        self._pad_y = 10

    def update(self, dt: float) -> None:
        """Update real elapsed time."""
        self.real_elapsed += dt

    def draw(self, screen: pygame.Surface) -> None:
        """Draw combined time display."""
        if not screen:
            return

        # Game time
        game_time_str = self.clock.get_formatted_time(self.use_12_hour)
        state = self.clock.get_current_state()
        day_str = f"Day {state.game_day}"

        # Real time
        real_total = int(self.real_elapsed)
        real_minutes = real_total // 60
        real_seconds = real_total % 60
        real_time_str = f"{real_minutes:02d}:{real_seconds:02d}"

        # Render text
        day_img = self._label_font.render(day_str, True, (200, 200, 200))
        game_img = self._time_font.render(game_time_str, True, (245, 245, 245))
        real_label_img = self._label_font.render("Real Time", True, (160, 160, 160))
        real_img = self._time_font.render(real_time_str, True, (180, 180, 180))

        # Calculate dimensions
        max_width = max(
            day_img.get_width(),
            game_img.get_width(),
            real_label_img.get_width(),
            real_img.get_width(),
        )
        block_w = max_width + self._pad_x * 2
        block_h = (
            day_img.get_height()
            + game_img.get_height()
            + real_label_img.get_height()
            + real_img.get_height()
            + self._pad_y * 5
        )

        # Background
        bg_rect = pygame.Rect(self.pos[0], self.pos[1], block_w, block_h)
        pygame.draw.rect(screen, (25, 25, 25), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 60), bg_rect, width=1, border_radius=8)

        # Draw text elements
        y_offset = self.pos[1] + self._pad_y

        # Day
        blit_text(
            screen,
            day_str,
            self._label_font,
            (self.pos[0] + self._pad_x, y_offset),
            (200, 200, 200),
            shadow=True,
        )
        y_offset += day_img.get_height() + 4

        # Game time
        blit_text(
            screen,
            game_time_str,
            self._time_font,
            (self.pos[0] + self._pad_x, y_offset),
            (245, 245, 245),
            shadow=True,
        )
        y_offset += game_img.get_height() + 8

        # Real time label
        blit_text(
            screen,
            "Real Time",
            self._label_font,
            (self.pos[0] + self._pad_x, y_offset),
            (160, 160, 160),
            shadow=True,
        )
        y_offset += real_label_img.get_height() + 4

        # Real time
        blit_text(
            screen,
            real_time_str,
            self._time_font,
            (self.pos[0] + self._pad_x, y_offset),
            (180, 180, 180),
            shadow=True,
        )
