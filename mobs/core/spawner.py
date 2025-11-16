from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Callable, Dict, Optional, Tuple

from constants import CHUNK_PIXELS, TILE_SIZE
from systems.mobs.core import behavior
from systems.time_manager_package.time_events import TimeEvent, TimeEventType, TimePhase
from systems.mobs.core.species_loader import MobSpec

if TYPE_CHECKING:
    from systems.time_manager_package.time_manager import TimeManager


class MobSpawner:
    """Heartbeat-driven mob spawning coordinator."""

    def __init__(
        self,
        time_manager: "TimeManager",
        species: Dict[str, MobSpec],
        spawn_callback: Callable[[str, Tuple[float, float]], None],
        count_callback: Callable[[str, Tuple[int, int]], int],
    ) -> None:
        self._time_manager = time_manager
        self._species = species
        self._spawn_callback = spawn_callback
        self._count_callback = count_callback
        self._player = None
        self._world = None
        self._active = False

    def start(self) -> None:
        if self._active:
            return
        self._time_manager.subscribe_to_event(
            TimeEventType.HEARTBEAT, self._handle_heartbeat
        )
        self._active = True

    def stop(self) -> None:
        if not self._active:
            return
        self._time_manager.unsubscribe_from_event(
            TimeEventType.HEARTBEAT, self._handle_heartbeat
        )
        self._active = False

    def update_context(self, player, world) -> None:
        self._player = player
        self._world = world

    def _handle_heartbeat(self, event: TimeEvent) -> None:
        if not self._active or self._player is None or self._world is None:
            return

        current_phase = self._time_manager.clock.get_current_phase()
        if current_phase not in (TimePhase.DUSK, TimePhase.NIGHT):
            return

        for spec in self._species.values():
            attempts = max(0, int(spec.spawn.attempts_per_heartbeat))
            if attempts <= 0:
                continue
            chance = float(spec.spawn.spawn_chance)
            if not (0.0 < chance <= 1.0):
                continue

            for _ in range(attempts):
                pos = self._pick_spawn_pos(spec)
                if pos is None:
                    continue
                chunk = self._chunk_for_pos(pos)
                if self._count_callback(spec.id, chunk) >= int(spec.spawn.max_alive):
                    continue
                if random.random() > chance:
                    continue
                self._spawn_callback(spec.id, pos)

    def _pick_spawn_pos(self, spec: MobSpec) -> Optional[Tuple[float, float]]:
        if self._player is None or self._world is None:
            return None

        px, py = getattr(self._player, "world_pos", (0.0, 0.0))
        rmin, rmax = spec.spawn.radius_px
        width = float(getattr(spec.assets, "frame_width", TILE_SIZE))
        height = float(getattr(spec.assets, "frame_height", TILE_SIZE))
        for _ in range(32):
            angle = random.uniform(0.0, math.tau)
            radius = random.uniform(rmin, rmax)
            x = px + math.cos(angle) * radius
            y = py + math.sin(angle) * radius
            dx, dy = x - px, y - py
            if (dx * dx + dy * dy) < (spec.stats.attack_range_px * 1.5) ** 2:
                continue
            if not behavior.can_spawn_at(
                self._world,
                (x, y),
                width=width,
                height=height,
            ):
                continue
            return (x, y)
        return None

    def _chunk_for_pos(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        x, y = pos
        cx = int(math.floor(x / CHUNK_PIXELS))
        cy = int(math.floor(y / CHUNK_PIXELS))
        return (cx, cy)


