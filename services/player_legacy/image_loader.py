from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pygame

from constants import PLAYER_SIZE

SPRITESHEET_FRAME_WIDTH = 115
SPRITESHEET_FRAME_HEIGHT = 115
DEFAULT_TARGET_HEIGHT = PLAYER_SIZE

_SHEET_CACHE: dict[str, pygame.Surface] = {}
_GRID_CACHE: dict[Tuple[str, int, int, int], Tuple[Tuple[pygame.Surface, ...], ...]] = {}
_ROW_CACHE: dict[Tuple[str, int, int, int, int, int], Tuple[pygame.Surface, ...]] = {}
_ASSET_ROOT_OVERRIDE: Optional[Path] = None


@dataclass(frozen=True)
class SpriteSheetSlice:
    filename: str
    row: int
    frames: int
    start_col: int = 0
    frame_width: int = SPRITESHEET_FRAME_WIDTH
    frame_height: int = SPRITESHEET_FRAME_HEIGHT
    target_height: int | None = DEFAULT_TARGET_HEIGHT


def set_player_asset_root(path: Path) -> None:
    """Override the legacy asset directory at runtime."""
    global _ASSET_ROOT_OVERRIDE
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"player asset root does not exist: {resolved}")
    _ASSET_ROOT_OVERRIDE = resolved


def _assets_dir() -> Path:
    if _ASSET_ROOT_OVERRIDE is not None:
        return _ASSET_ROOT_OVERRIDE
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    return repo_root / "assets" / "player"


def _asset_path(filename: str) -> str:
    base = _assets_dir()
    path = (base / filename).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Sprite not found: {path}")
    return path.as_posix()


def _load_surface(filename: str) -> pygame.Surface:
    cached = _SHEET_CACHE.get(filename)
    if cached is not None:
        return cached
    path = _asset_path(filename)
    surf = pygame.image.load(path).convert_alpha()
    _SHEET_CACHE[filename] = surf
    return surf


def _scale_frame(frame: pygame.Surface, target_height: int | None) -> pygame.Surface:
    if target_height is None:
        return frame
    if target_height <= 0:
        raise ValueError("target_height must be positive")
    width, height = frame.get_size()
    if height == 0:
        raise ValueError("frame height must be positive")
    if height == target_height:
        return frame
    scale = target_height / float(height)
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    return pygame.transform.smoothscale(frame, (new_width, new_height))


def load_spritesheet_grid(
    filename: str,
    *,
    frame_width: int = SPRITESHEET_FRAME_WIDTH,
    frame_height: int = SPRITESHEET_FRAME_HEIGHT,
    target_height: int | None = DEFAULT_TARGET_HEIGHT,
) -> Tuple[Tuple[pygame.Surface, ...], ...]:
    """Load an entire spritesheet and return a row/column grid of frames."""
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")

    cache_key = (filename, frame_width, frame_height, target_height or 0)
    cached = _GRID_CACHE.get(cache_key)
    if cached is not None:
        return cached

    sheet = _load_surface(filename)
    sheet_width, sheet_height = sheet.get_size()
    if sheet_width % frame_width != 0 or sheet_height % frame_height != 0:
        raise ValueError(
            f"Spritesheet {filename} size {sheet_width}x{sheet_height} "
            f"is not divisible by frame {frame_width}x{frame_height}"
        )

    columns = sheet_width // frame_width
    rows = sheet_height // frame_height

    grid: List[Tuple[pygame.Surface, ...]] = []
    for row in range(rows):
        frames: List[pygame.Surface] = []
        for col in range(columns):
            rect = pygame.Rect(
                col * frame_width,
                row * frame_height,
                frame_width,
                frame_height,
            )
            frame = sheet.subsurface(rect).copy()
            scaled = _scale_frame(frame, target_height)
            frames.append(scaled)
        grid.append(tuple(frames))

    result = tuple(grid)
    _GRID_CACHE[cache_key] = result
    return result


def load_spritesheet_row(
    filename: str,
    row: int,
    *,
    frame_count: int | None = None,
    start_col: int = 0,
    frame_width: int = SPRITESHEET_FRAME_WIDTH,
    frame_height: int = SPRITESHEET_FRAME_HEIGHT,
    target_height: int | None = DEFAULT_TARGET_HEIGHT,
) -> Tuple[pygame.Surface, ...]:
    """Retrieve a contiguous slice of frames from a spritesheet row."""
    if row < 0:
        raise ValueError("row index must be non-negative")
    if start_col < 0:
        raise ValueError("start_col must be non-negative")

    key = (
        filename,
        row,
        start_col,
        frame_count or -1,
        frame_width,
        target_height or 0,
    )
    cached = _ROW_CACHE.get(key)
    if cached is not None:
        return cached

    grid = load_spritesheet_grid(
        filename,
        frame_width=frame_width,
        frame_height=frame_height,
        target_height=target_height,
    )
    if row >= len(grid):
        raise IndexError(f"row {row} out of range for spritesheet {filename}")

    row_frames = grid[row]
    end_col = len(row_frames) if frame_count is None else start_col + frame_count
    if end_col > len(row_frames):
        raise IndexError(
            f"Requested frames exceed available columns in {filename}: "
            f"start={start_col}, count={frame_count}, columns={len(row_frames)}"
        )

    result = tuple(row_frames[start_col:end_col])
    _ROW_CACHE[key] = result
    return result


def load_png(filename: str) -> pygame.Surface:
    """Load a single-frame sprite (legacy helper)."""
    surface = _load_surface(filename)
    return _scale_frame(surface.copy(), DEFAULT_TARGET_HEIGHT)


def _frames_from_slice(spec: SpriteSheetSlice) -> List[pygame.Surface]:
    return list(
        load_spritesheet_row(
            spec.filename,
            row=spec.row,
            frame_count=spec.frames,
            start_col=spec.start_col,
            frame_width=spec.frame_width,
            frame_height=spec.frame_height,
            target_height=spec.target_height,
        )
    )


def load_sequence(resource: Sequence[str] | SpriteSheetSlice | str) -> List[pygame.Surface]:
    """Load animation frames from either legacy PNG lists or spritesheet slices."""
    if isinstance(resource, SpriteSheetSlice):
        return _frames_from_slice(resource)
    if isinstance(resource, str):
        return [load_png(resource)]
    frames: List[pygame.Surface] = []
    for entry in resource:
        if isinstance(entry, SpriteSheetSlice):
            frames.extend(_frames_from_slice(entry))
        else:
            frames.extend(load_sequence(entry))
    return frames
