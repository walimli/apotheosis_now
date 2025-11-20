from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pygame

from services.asset_loader.notification_assets import ButtonImages


@dataclass(frozen=True)
class AnimationFrames:
    """Container for a single animation sequence."""

    frames: List[pygame.Surface]
    frame_time: float
    loop: bool = True


class CraftingAssets:
    """Loader for crafting UI assets (button + atlas animations)."""

    DEFAULT_FRAME_TIME = 0.1

    def __init__(self, frame_time: float = DEFAULT_FRAME_TIME) -> None:
        self._frame_time = float(frame_time)
        project_root = Path(__file__).resolve().parents[2]
        ui_root = project_root / "assets" / "ui"
        button_root = ui_root / "buttons" / "crafting_button"
        atlas_root = ui_root / "crafting_atlas"

        self.crafting_button_images = self._load_button_images(button_root)
        self.atlas_loops: Dict[int, AnimationFrames] = {
            stage: AnimationFrames(
                frames=self._load_sequence(atlas_root / f"atlas_{stage}"),
                frame_time=self._frame_time,
                loop=True,
            )
            for stage in range(1, 5)
        }
        self.success_animation = AnimationFrames(
            frames=self._load_sequence(atlas_root / "crafting_success"),
            frame_time=self._frame_time,
            loop=False,
        )
        self.failure_animation = AnimationFrames(
            frames=self._load_sequence(atlas_root / "crafting_failure"),
            frame_time=self._frame_time,
            loop=False,
        )

    def _load_button_images(self, root: Path) -> ButtonImages:
        if not root.exists():
            raise FileNotFoundError(f"Crafting button assets missing: {root}")
        normal = self._load_surface(root / "crafting_button.png")
        hover = self._load_surface(root / "crafting_hover.png")
        pressed = self._load_surface(root / "crafting_press.png")
        return ButtonImages(normal=normal, hover=hover, pressed=pressed)

    def _load_sequence(self, folder: Path) -> List[pygame.Surface]:
        if not folder.exists():
            raise FileNotFoundError(f"Crafting atlas sequence missing: {folder}")
        frames = []
        for path in sorted(folder.glob("*.png"), key=self._sort_key):
            frames.append(self._load_surface(path))
        if not frames:
            raise ValueError(f"No frames found in crafting atlas sequence: {folder}")
        return frames

    def _load_surface(self, path: Path) -> pygame.Surface:
        if not path.exists():
            raise FileNotFoundError(f"Crafting asset missing: {path}")
        return pygame.image.load(str(path)).convert_alpha()

    @staticmethod
    def _sort_key(path: Path):
        stem = path.stem
        try:
            suffix = stem.rsplit("_", 1)[1]
            return (0, int(suffix))
        except (IndexError, ValueError):
            return (1, stem)


__all__ = [
    "CraftingAssets",
    "AnimationFrames",
]
