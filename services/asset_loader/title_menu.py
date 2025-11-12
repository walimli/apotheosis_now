"""Asset loading utilities for the title menu system."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple

import pygame

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_DIR = _PROJECT_ROOT / "assets"
_FONT_PATH = _ASSETS_DIR / "ui" / "fonts" / "system.ttf"
_BUTTON_IMAGE_DIR = _ASSETS_DIR / "ui" / "buttons" / "menu_button"

_ALPHA_THRESHOLD = 32
_TEXT_COLOR = (255, 255, 255)
_TEXT_MARGIN = 48

_BUTTON_VARIANTS = {
    "normal": "normal.png",
    "hover": "hover.png",
    "pressed": "press.png",
}


def _check_environment() -> None:
    if not _BUTTON_IMAGE_DIR.exists():
        raise FileNotFoundError(f"Button art directory missing: {_BUTTON_IMAGE_DIR}")
    if not _FONT_PATH.exists():
        raise FileNotFoundError(f"Title font missing: {_FONT_PATH}")


@lru_cache(maxsize=None)
def _base_button_surface(state: str) -> pygame.Surface:
    _check_environment()
    filename = _BUTTON_VARIANTS[state]
    path = _BUTTON_IMAGE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing '{state}' sprite for menu buttons: {path}")
    return pygame.image.load(str(path)).convert_alpha()


@lru_cache(maxsize=None)
def _labelled_surfaces(label: str) -> Dict[str, pygame.Surface]:
    label_text = label.strip().upper()
    if not label_text:
        label_text = "BUTTON"

    base_surfaces = {state: _base_button_surface(state).copy() for state in _BUTTON_VARIANTS}
    text_surface = _render_label(label_text, base_surfaces["normal"].get_rect())

    for state, surface in base_surfaces.items():
        _blit_text_center(surface, text_surface)
    return base_surfaces


def load_button_images(button_key: str, label: str) -> Dict[str, pygame.Surface]:
    """Return the menu button surfaces for the given logical key and label."""
    del button_key  # Logical key kept for API stability; surfaces driven by label now.
    labelled = _labelled_surfaces(label)
    # Return fresh copies so callers can safely transform them if needed.
    return {state: surface.copy() for state, surface in labelled.items()}


@lru_cache(maxsize=None)
def button_vertical_bounds(button_key: str) -> Tuple[int, int]:
    del button_key
    surface = _base_button_surface("normal")
    alpha = pygame.surfarray.array_alpha(surface)
    mask = alpha >= _ALPHA_THRESHOLD
    rows = mask.any(axis=0)
    indices = rows.nonzero()[0]
    if indices.size == 0:
        height = surface.get_height()
        return 0, height - 1
    top = int(indices[0])
    bottom = int(indices[-1])
    return top, bottom


def get_title_font(display, size: int) -> pygame.font.Font:
    """Return the scaled title font from the display helper."""
    _check_environment()
    return display.get_scaled_font(str(_FONT_PATH), size)


def _render_label(text: str, target_rect: pygame.Rect) -> pygame.Surface:
    max_width = target_rect.width - _TEXT_MARGIN
    max_height = target_rect.height - _TEXT_MARGIN
    font_size = min(int(target_rect.height * 0.42), max_height)
    font_size = max(font_size, 16)

    font = pygame.font.Font(str(_FONT_PATH), font_size)
    rendered = font.render(text, True, _TEXT_COLOR)
    while rendered.get_width() > max_width and font_size > 16:
        font_size -= 2
        font = pygame.font.Font(str(_FONT_PATH), font_size)
        rendered = font.render(text, True, _TEXT_COLOR)

    return rendered


def _blit_text_center(surface: pygame.Surface, text_surface: pygame.Surface) -> None:
    text_rect = text_surface.get_rect(center=surface.get_rect().center)
    surface.blit(text_surface, text_rect)
