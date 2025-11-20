from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Hashable, Optional, Tuple

import pygame

from .placeables_asset_loader import PlaceablesAssetLoader, PlaceableSpriteBundle
from .placeables_json_reader import PlaceableRecord


class PlaceableAnimator:
    """Advance and expose animation frames for a placeable sprite bundle."""

    def __init__(
        self,
        bundle: PlaceableSpriteBundle,
        *,
        frame_duration: float = 0.20,
        loop: bool = True,
    ) -> None:
        self._bundle = bundle
        self._frame_duration = max(1e-3, float(frame_duration))
        self._loop = loop
        self._elapsed = 0.0
        self._frame_index = 0
        self._playing = bundle.is_animated

    @property
    def bundle(self) -> PlaceableSpriteBundle:
        return self._bundle

    def set_bundle(self, bundle: PlaceableSpriteBundle) -> None:
        self._bundle = bundle
        self.reset()
        self._playing = bundle.is_animated

    def reset(self) -> None:
        self._elapsed = 0.0
        self._frame_index = 0
        self._playing = self._bundle.is_animated

    def update(self, dt: float) -> None:
        if not self._bundle.is_animated or not self._playing:
            return
        self._elapsed += max(0.0, float(dt))
        while self._elapsed >= self._frame_duration:
            self._elapsed -= self._frame_duration
            self._frame_index += 1
            frames = self._bundle.animation.frame_count if self._bundle.animation else 1
            if self._frame_index >= frames:
                if self._loop:
                    self._frame_index = 0
                else:
                    self._frame_index = frames - 1
                    self._playing = False
                    break

    def current_frame(self) -> pygame.Surface:
        return self._bundle.frame(self._frame_index)

    def is_playing(self) -> bool:
        return self._playing


@dataclass
class _AnimationEntry:
    dataset_name: Optional[str]
    record: PlaceableRecord
    bundle: PlaceableSpriteBundle
    animator: Optional[PlaceableAnimator]
    sprite_id: str


class PlaceableAnimationController:
    """Manage per-instance animators and keep object sprite caches in sync."""

    def __init__(
        self,
        asset_loader: PlaceablesAssetLoader,
        object_sprites: Dict[str, pygame.Surface],
        *,
        sprite_id_factory: Optional[Callable[[Optional[str], str], str]] = None,
        scale_cache: Optional[Dict[Tuple[str, float], pygame.Surface]] = None,
        frame_duration: float = 0.12,
        loop: bool = True,
    ) -> None:
        self._asset_loader = asset_loader
        self._object_sprites = object_sprites
        self._scale_cache = scale_cache
        self._sprite_id_factory = sprite_id_factory or self._default_sprite_id
        self._frame_duration = frame_duration
        self._loop = loop
        self._entries: Dict[Hashable, _AnimationEntry] = {}

    # --- Public API -----------------------------------------------------
    def sprite_id_for(self, dataset_name: Optional[str], record_key: str) -> str:
        return self._sprite_id_factory(dataset_name, record_key)

    def register_instance(
        self,
        handle: Hashable,
        dataset_name: Optional[str],
        record: PlaceableRecord,
    ) -> str:
        bundle = self._asset_loader.load_bundle(record)
        sprite_id = self.sprite_id_for(dataset_name, record.key)
        animator = (
            PlaceableAnimator(
                bundle, frame_duration=self._frame_duration, loop=self._loop
            )
            if bundle.is_animated
            else None
        )
        self._entries[handle] = _AnimationEntry(
            dataset_name=dataset_name,
            record=record,
            bundle=bundle,
            animator=animator,
            sprite_id=sprite_id,
        )
        self._store_surface(sprite_id, self._current_frame(bundle, animator), record)
        return sprite_id

    def update_instance(
        self,
        handle: Hashable,
        dataset_name: Optional[str],
        record: PlaceableRecord,
    ) -> str:
        bundle = self._asset_loader.load_bundle(record)
        sprite_id = self.sprite_id_for(dataset_name, record.key)
        entry = self._entries.get(handle)
        if entry is None:
            animator = (
                PlaceableAnimator(
                    bundle, frame_duration=self._frame_duration, loop=self._loop
                )
                if bundle.is_animated
                else None
            )
            self._entries[handle] = _AnimationEntry(
                dataset_name=dataset_name,
                record=record,
                bundle=bundle,
                animator=animator,
                sprite_id=sprite_id,
            )
        else:
            entry.dataset_name = dataset_name
            entry.record = record
            entry.bundle = bundle
            entry.sprite_id = sprite_id
            if bundle.is_animated:
                if entry.animator is None:
                    entry.animator = PlaceableAnimator(
                        bundle, frame_duration=self._frame_duration, loop=self._loop
                    )
                else:
                    entry.animator.set_bundle(bundle)
                    entry.animator.reset()
            else:
                entry.animator = None
        self._store_surface(
            sprite_id,
            self._current_frame(bundle, self._entries[handle].animator),
            record,
        )
        return sprite_id

    def advance(self, dt: float) -> None:
        delta = max(0.0, float(dt))
        if delta <= 0.0:
            return
        for entry in self._entries.values():
            animator = entry.animator
            if animator is None:
                continue
            animator.update(delta)
            frame = animator.current_frame()
            self._store_surface(entry.sprite_id, frame, entry.record)

    def unregister(self, handle: Hashable) -> None:
        entry = self._entries.pop(handle, None)
        if not entry:
            return
        self._invalidate_scale_cache(entry.sprite_id)

    # --- Internal helpers -----------------------------------------------
    @staticmethod
    def _default_sprite_id(dataset_name: Optional[str], record_key: str) -> str:
        if dataset_name:
            return f"{dataset_name}:{record_key}"
        return record_key

    def _current_frame(
        self,
        bundle: PlaceableSpriteBundle,
        animator: Optional[PlaceableAnimator],
    ) -> pygame.Surface:
        if animator is not None:
            return animator.current_frame()
        return bundle.frame(0)

    def _store_surface(
        self,
        sprite_id: str,
        frame: pygame.Surface,
        record: PlaceableRecord,
    ) -> None:
        surface = frame
        scale = float(record.scale or 1.0)
        if abs(scale - 1.0) > 1e-6:
            width = max(1, int(round(frame.get_width() * scale)))
            height = max(1, int(round(frame.get_height() * scale)))
            surface = pygame.transform.smoothscale(frame, (width, height))
        self._object_sprites[sprite_id] = surface
        self._invalidate_scale_cache(sprite_id)

    def _invalidate_scale_cache(self, sprite_id: str) -> None:
        cache = self._scale_cache
        if not cache:
            return
        keys = [
            key
            for key in cache.keys()
            if isinstance(key, tuple) and key and key[0] == sprite_id
        ]
        for key in keys:
            cache.pop(key, None)


__all__ = ["PlaceableAnimator", "PlaceableAnimationController"]
