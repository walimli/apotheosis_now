from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pygame

from .placeables_json_reader import AnimationSheetSpec, PlaceableRecord

Surface = pygame.Surface


class PlaceableAnimation:
    """Lightweight container for animation frames."""

    def __init__(self, frames: Iterable[Surface]) -> None:
        frames_list = list(frames)
        if not frames_list:
            raise ValueError("PlaceableAnimation requires at least one frame")
        self._frames = frames_list

    @property
    def frames(self) -> Tuple[Surface, ...]:
        return tuple(self._frames)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    def first_frame(self) -> Surface:
        return self._frames[0]

    def frame_at(self, index: int) -> Surface:
        if not self._frames:
            raise IndexError("No frames in animation")
        return self._frames[index % len(self._frames)]


class PlaceableSpriteBundle:
    """Bundle containing either a static sprite or animation for a placeable."""

    def __init__(
        self,
        record: PlaceableRecord,
        image: Surface,
        animation: Optional[PlaceableAnimation] = None,
    ) -> None:
        self.record = record
        self.image = image
        self.animation = animation

    @property
    def is_animated(self) -> bool:
        return self.animation is not None

    def frame(self, index: int = 0) -> Surface:
        if self.animation is None:
            return self.image
        return self.animation.frame_at(index)


class PlaceablesAssetLoader:
    """Load placeable sprites and animation loops from disk."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self._cache: Dict[str, PlaceableSpriteBundle] = {}
        self._sheet_cache: Dict[Tuple[str, int, int], Surface] = {}
        self._sheet_frames_cache: Dict[Tuple[str, int, int, int, int], Tuple[Surface, ...]] = {}

    def load_bundle(self, record: PlaceableRecord) -> PlaceableSpriteBundle:
        key = record.image_path
        if key in self._cache:
            return self._cache[key]

        animation = None
        image: Optional[Surface] = None
        frames: Optional[Tuple[Surface, ...]] = None

        if record.animation_sheet:
            frames = self._load_sheet_frames(record.animation_sheet)
            if not frames:
                raise ValueError(f"Spritesheet '{record.animation_sheet.sheet_path}' produced no frames")
            image = frames[0]
            if record.animation:
                animation = PlaceableAnimation(frames)

        if image is None:
            image = self._load_image(record.image_path)

        if record.animation and animation is None:
            animation_frames = self._load_legacy_animation(record.image_path, fallback=image)
            if animation_frames is not None:
                animation = PlaceableAnimation(animation_frames)

        bundle = PlaceableSpriteBundle(record=record, image=image, animation=animation)
        self._cache[key] = bundle
        return bundle

    def clear_cache(self) -> None:
        self._cache.clear()
        self._sheet_cache.clear()
        self._sheet_frames_cache.clear()

    def _load_image(self, relative_path: str) -> Surface:
        full_path = (self._project_root / relative_path).resolve()
        if not full_path.is_file():
            fallback_dir = full_path.parent
            if fallback_dir.is_dir():
                candidates = sorted(fallback_dir.glob("*.png"))
                if candidates:
                    full_path = candidates[0]
        if not full_path.is_file():
            raise FileNotFoundError(f"Placeable sprite not found: {full_path}")
        return pygame.image.load(str(full_path)).convert_alpha()

    def _load_legacy_animation(self, base_path: str, fallback: Surface) -> Optional[Iterable[Surface]]:
        image_path = Path(base_path)
        directory = image_path.parent
        stem = image_path.stem
        prefix = stem
        if "_" in stem:
            head, tail = stem.rsplit("_", 1)
            if tail.isdigit():
                prefix = head
        folder = (self._project_root / directory).resolve()
        if not folder.exists():
            return PlaceableAnimation([fallback])

        frames: list[Surface] = []
        candidates = sorted(folder.glob(f"{prefix}_*.png"))
        if not candidates:
            candidates = sorted(folder.glob("*.png"))
        for candidate in candidates:
            try:
                frame = pygame.image.load(str(candidate)).convert_alpha()
            except Exception:
                continue
            frames.append(frame)

        if not frames:
            frames.append(fallback)

        return frames

    def _load_sheet_surface(self, spec: AnimationSheetSpec) -> Surface:
        cache_key = (spec.sheet_path, spec.columns, spec.rows)
        cached = self._sheet_cache.get(cache_key)
        if cached is not None:
            return cached
        full_path = (self._project_root / spec.sheet_path).resolve()
        if not full_path.is_file():
            raise FileNotFoundError(f"Placeable spritesheet not found: {full_path}")
        surface = pygame.image.load(str(full_path)).convert_alpha()
        self._sheet_cache[cache_key] = surface
        return surface

    def _load_sheet_frames(self, spec: AnimationSheetSpec) -> Tuple[Surface, ...]:
        frame_count = spec.effective_frames
        cache_key = (spec.sheet_path, spec.columns, spec.rows, frame_count, spec.start_index)
        cached = self._sheet_frames_cache.get(cache_key)
        if cached is not None:
            return cached

        sheet = self._load_sheet_surface(spec)
        width, height = sheet.get_size()
        if width % spec.columns != 0 or height % spec.rows != 0:
            raise ValueError(
                f"Spritesheet '{spec.sheet_path}' size {width}x{height} not divisible by grid "
                f"{spec.columns}x{spec.rows}"
            )
        frame_width = width // spec.columns
        frame_height = height // spec.rows

        total_slots = spec.columns * spec.rows
        start = min(spec.start_index, total_slots - 1 if total_slots else 0)
        frames_to_extract = max(0, min(frame_count, total_slots - start))

        frames: List[Surface] = []
        index = start
        for _ in range(frames_to_extract):
            row = index // spec.columns
            col = index % spec.columns
            rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
            frames.append(sheet.subsurface(rect).copy())
            index += 1

        if not frames and sheet is not None:
            rect = pygame.Rect(0, 0, frame_width, frame_height)
            frames.append(sheet.subsurface(rect).copy())

        result = tuple(frames)
        self._sheet_frames_cache[cache_key] = result
        return result


__all__ = [
    "PlaceablesAssetLoader",
    "PlaceableSpriteBundle",
    "PlaceableAnimation",
]
