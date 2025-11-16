from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import pygame


@dataclass(frozen=True)
class WispSummonAnimationConfig:
    sheet_path: Path = Path("assets/mobs/wisp/summon_wisp.png")
    columns: int = 5
    rows: int = 3
    frame_width: int = 64
    frame_height: int = 64
    frame_duration: float = 0.2


def load_summon_frames(
    config: WispSummonAnimationConfig | None = None,
) -> Tuple[List[pygame.Surface], float]:
    cfg = config or WispSummonAnimationConfig()
    sheet = _load_sheet(cfg.sheet_path)
    frames: List[pygame.Surface] = []

    for row in range(cfg.rows):
        for col in range(cfg.columns):
            rect = pygame.Rect(
                col * cfg.frame_width,
                row * cfg.frame_height,
                cfg.frame_width,
                cfg.frame_height,
            )
            frame = sheet.subsurface(rect).copy()
            frames.append(frame)

    return frames, cfg.frame_duration


def _load_sheet(path: Path) -> pygame.Surface:
    sheet_path = Path(path)
    if not sheet_path.is_file():
        raise FileNotFoundError(f"Wisp summon sprite sheet not found: {sheet_path}")
    return pygame.image.load(sheet_path.as_posix()).convert_alpha()
