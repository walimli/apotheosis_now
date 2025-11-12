from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import pygame

from .registry_reader import SoundRegistry, load_sound_registry


class AudioManager:
    """Load and play sound effects referenced in the editable registry."""

    def __init__(
        self, registry_path: Path, *, sfx_volume: float = 0.5, music_volume: float = 0.2
    ) -> None:
        self._ensure_mixer()
        self.registry: SoundRegistry = load_sound_registry(registry_path)
        pygame.mixer.set_num_channels(self._determine_channel_pool_size())
        self._sfx_volume = self._clamp_volume(sfx_volume)
        self._music_volume = self._clamp_volume(music_volume)
        self._sfx_cache: Dict[str, pygame.mixer.Sound] = {}
        self._looping_channels: Dict[str, pygame.mixer.Channel] = {}
        self._active_music_key: Optional[str] = None
        self._active_music_path: Optional[Path] = None
        pygame.mixer.music.set_volume(self._music_volume)

    @staticmethod
    def _ensure_mixer() -> None:
        if pygame.mixer.get_init() is not None:
            return
        pygame.mixer.init()

    @staticmethod
    def _clamp_volume(value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Volume must be between 0.0 and 1.0, received {value}")
        return float(value)

    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume

    def set_sfx_volume(self, value: float) -> None:
        self._sfx_volume = self._clamp_volume(value)
        for channel in list(self._looping_channels.values()):
            if channel.get_busy():
                channel.set_volume(self._sfx_volume)

    @property
    def music_volume(self) -> float:
        return self._music_volume

    def set_music_volume(self, value: float) -> None:
        self._music_volume = self._clamp_volume(value)
        pygame.mixer.music.set_volume(self._music_volume)

    # --- Sound effects -----------------------------------------------------
    def play_once(self, event_key: str) -> None:
        sound = self._require_sound(event_key)
        sound.set_volume(self._sfx_volume)
        channel = sound.play()
        if channel is None:
            raise RuntimeError(
                f"Unable to play sound for event '{event_key}' - all channels busy"
            )
        channel.set_volume(self._sfx_volume)

    def start_loop(self, event_key: str) -> None:
        if event_key in self._looping_channels:
            channel = self._looping_channels[event_key]
            if channel.get_busy():
                return
        sound = self._require_sound(event_key)
        sound.set_volume(self._sfx_volume)
        channel = sound.play(loops=-1)
        if channel is None:
            raise RuntimeError(f"Unable to start looping sound for event '{event_key}'")
        channel.set_volume(self._sfx_volume)
        self._looping_channels[event_key] = channel

    def stop_loop(self, event_key: str) -> None:
        channel = self._looping_channels.get(event_key)
        if channel is None:
            return
        if channel.get_busy():
            channel.stop()
        self._looping_channels.pop(event_key, None)

    def stop_all_loops(self) -> None:
        for key in list(self._looping_channels.keys()):
            self.stop_loop(key)

    # --- Music -------------------------------------------------------------
    def play_music(self, track_key: str) -> None:
        path = self.registry.resolve_music(track_key)
        if self._active_music_path == path and pygame.mixer.music.get_busy():
            return
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.set_volume(self._music_volume)
        pygame.mixer.music.play(-1)
        self._active_music_key = track_key
        self._active_music_path = path

    def stop_music(self) -> None:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self._active_music_key = None
        self._active_music_path = None

    def _determine_channel_pool_size(self) -> int:
        """Provision enough mixer channels for all one-shot SFX plus a small buffer."""
        unique_events = len(self.registry.events)
        return max(16, unique_events + 4)

    # --- Internals --------------------------------------------------------
    def _require_sound(self, event_key: str) -> pygame.mixer.Sound:
        if event_key in self._sfx_cache:
            return self._sfx_cache[event_key]
        path = self.registry.resolve_event(event_key)
        sound = pygame.mixer.Sound(str(path))
        self._sfx_cache[event_key] = sound
        return sound


__all__ = ["AudioManager"]
