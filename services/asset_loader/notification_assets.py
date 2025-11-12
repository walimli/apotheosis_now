"""Notification asset loader utilities for the notifications UI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSET_ROOT = _PROJECT_ROOT / "assets" / "ui"
_PANELS_DIR = _ASSET_ROOT / "panels"
_BIG_BUTTON_DIR = _ASSET_ROOT / "buttons" / "big_button"
_MENU_BUTTON_DIR = _ASSET_ROOT / "buttons" / "menu_button"
_FONT_PATH = _ASSET_ROOT / "fonts" / "system.ttf"


@dataclass(frozen=True)
class ButtonImages:
    normal: pygame.Surface
    hover: pygame.Surface
    pressed: pygame.Surface


class NotificationUIAssets:
    """Load and expose notification UI surfaces from the shared asset pool."""

    def __init__(self) -> None:
        self.panel_surface = self._load_surface(_PANELS_DIR / "system_panel.png")
        self.notification_window = self._load_surface(
            _PANELS_DIR / "landscape_panel.png"
        )
        self.exit_icon = self._load_surface(_PANELS_DIR / "exit.png")
        self.system_button_images = self._load_button_set(
            _BIG_BUTTON_DIR,
            normal_name="system_button.png",
            hover_name="system_hover.png",
            pressed_name="system_press.png",
        )
        self.panel_button_images = self._load_button_set(
            _MENU_BUTTON_DIR,
            normal_name="normal.png",
            hover_name="hover.png",
            pressed_name="press.png",
        )
        self.notification_panel_button_images = self._load_button_set(
            _MENU_BUTTON_DIR,
            normal_name="normal.png",
            hover_name="hover.png",
            pressed_name="press.png",
        )

    def font_path(self) -> Path:
        """Return the path to system.ttf used for text rendering."""
        if not _FONT_PATH.exists():
            raise FileNotFoundError(f"Notification UI font missing: {_FONT_PATH}")
        return _FONT_PATH

    def _load_surface(self, path: Path) -> pygame.Surface:
        if not path.exists():
            raise FileNotFoundError(f"Notification UI asset missing: {path}")
        return pygame.image.load(str(path)).convert_alpha()

    def _load_button_set(
        self,
        folder: Path,
        *,
        normal_name: str,
        hover_name: str,
        pressed_name: str,
    ) -> ButtonImages:
        if not folder.exists():
            raise FileNotFoundError(f"Notification UI button set missing: {folder}")
        normal = self._load_surface(folder / normal_name)
        hover = self._load_surface(folder / hover_name)
        pressed = self._load_surface(folder / pressed_name)
        return ButtonImages(normal=normal, hover=hover, pressed=pressed)


__all__ = ["NotificationUIAssets", "ButtonImages"]
