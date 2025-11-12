from __future__ import annotations

from typing import Callable, Dict, Optional

from services.time.time_events import TimeEvent, TimeEventType

from .manager import AudioManager
from .throttle import EventThrottle


_TIME_EVENT_MAP: Dict[TimeEventType, str] = {
    TimeEventType.DAWN_STARTED: "time.dawn_started",
    TimeEventType.DAY_STARTED: "time.day_started",
    TimeEventType.NOON_REACHED: "time.noon_reached",
    TimeEventType.DUSK_STARTED: "time.dusk_started",
    TimeEventType.NIGHT_STARTED: "time.night_started",
    TimeEventType.MIDNIGHT_REACHED: "time.midnight_reached",
    TimeEventType.HEARTBEAT: "time.heartbeat",
}

_DEFAULT_COOLDOWNS: Dict[str, float] = {
    "player.health_lost": 0.2,
    "mob.attack": 0.15,
}


class AudioEventListener:
    """Translate game events into audio playback via the audio manager."""

    def __init__(self, manager: AudioManager) -> None:
        self._manager = manager
        self._time_manager = None
        self._time_handlers: Dict[TimeEventType, Callable[[TimeEvent], None]] = {}
        self._throttle = EventThrottle(_DEFAULT_COOLDOWNS)

    # --- Generic event publication ---------------------------------------
    def publish(self, event_key: str) -> None:
        if not self._throttle.allow(event_key):
            return
        self._manager.play_once(event_key)

    def start_loop(self, event_key: str) -> None:
        self._manager.start_loop(event_key)

    def stop_loop(self, event_key: str) -> None:
        self._manager.stop_loop(event_key)

    # --- Time manager integration ----------------------------------------
    def attach_time_manager(self, time_manager) -> None:
        if self._time_manager is time_manager:
            return
        if self._time_manager is not None:
            self.detach_time_manager()
        self._time_manager = time_manager
        self._time_handlers = {}
        for event_type, key in _TIME_EVENT_MAP.items():
            def handler(event: TimeEvent, key: str = key) -> None:
                del event
                self.publish(key)

            time_manager.subscribe_to_event(event_type, handler)
            self._time_handlers[event_type] = handler

    def detach_time_manager(self) -> None:
        if self._time_manager is None:
            return
        for event_type, handler in self._time_handlers.items():
            self._time_manager.unsubscribe_from_event(event_type, handler)
        self._time_handlers.clear()
        self._time_manager = None
        self._throttle.clear()

    # --- State management -------------------------------------------------
    def on_state_changed(self, state_name: str) -> None:
        self._manager.stop_all_loops()
        track_key = f"state.{state_name}"
        self._manager.play_music(track_key)

    def stop_music(self) -> None:
        self._manager.stop_music()


_listener: Optional[AudioEventListener] = None


def set_global_listener(listener: AudioEventListener) -> None:
    global _listener
    _listener = listener


def require_listener() -> AudioEventListener:
    if _listener is None:
        raise RuntimeError("Audio listener has not been initialised")
    return _listener


def publish_audio_event(event_key: str) -> None:
    require_listener().publish(event_key)


def start_looping_event(event_key: str) -> None:
    require_listener().start_loop(event_key)


def stop_looping_event(event_key: str) -> None:
    require_listener().stop_loop(event_key)


def on_state_changed(state_name: str) -> None:
    require_listener().on_state_changed(state_name)


def attach_time_manager(time_manager) -> None:
    require_listener().attach_time_manager(time_manager)


def detach_time_manager() -> None:
    require_listener().detach_time_manager()


def stop_music() -> None:
    require_listener().stop_music()


__all__ = [
    "AudioEventListener",
    "attach_time_manager",
    "detach_time_manager",
    "on_state_changed",
    "publish_audio_event",
    "set_global_listener",
    "start_looping_event",
    "stop_looping_event",
    "stop_music",
]


