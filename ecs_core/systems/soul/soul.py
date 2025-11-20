from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from ecs_core.components import Position, Soul
from ecs_core.entities.entities import Entity
from ecs_core.systems_base import System
from services.time.time_events import TimeEvent, TimeEventType, TimePhase

from .safe_zone import SafeZoneComponent, safe_zone_contains_position

if TYPE_CHECKING:
    from services.time.time_manager import TimeManager
    from ecs_core.worlds.world import World


class SoulCosts:
    """Centralized, easily tunable soul economy knobs."""

    HEARTBEAT: int = 1
    LANDSCAPE_HARVEST: int = 1
    LANDSCAPE_PLACE: int = 1
    FARMING_HARVEST: int = 1
    COMBAT_ATTACK: int = 1
    CRAFTING_DEFAULT: int = 1


def should_drain_on_heartbeat(event: TimeEvent, *, in_safe_zone: bool = False) -> bool:
    """Determine if the heartbeat should drain soul for the given event."""
    if in_safe_zone:
        return False
    if event is None:
        return True
    phase = getattr(event, "phase", None)
    if phase is None:
        return bool(getattr(event, "is_day", True))
    if isinstance(phase, TimePhase):
        return phase is TimePhase.DAY
    try:
        coerced = TimePhase(str(phase))
    except Exception:
        return bool(getattr(event, "is_day", True))
    return coerced is TimePhase.DAY


class SoulSystem(System):
    """Event-driven soul drain/restore controller."""

    def __init__(
        self,
        world: "World",
        time_manager: Optional["TimeManager"],
        *,
        heartbeat_cost: int = SoulCosts.HEARTBEAT,
        tile_size: int = 64,
    ) -> None:
        super().__init__(world)
        self._time_manager = time_manager
        self._heartbeat_cost = max(0, int(heartbeat_cost))
        normalized_tile_size = tile_size if tile_size and tile_size > 0 else 1
        self._tile_size = max(1, int(normalized_tile_size))
        self._subscribed = False
        self._subscribe_to_time_events()

    def _subscribe_to_time_events(self) -> None:
        if self._time_manager is None or self._subscribed:
            return
        self._time_manager.subscribe_to_event(TimeEventType.HEARTBEAT, self._handle_heartbeat)
        self._subscribed = True

    def shutdown(self) -> None:
        """Unsubscribe from time events when the system is torn down."""
        if self._time_manager is None or not self._subscribed:
            return
        self._time_manager.unsubscribe_from_event(TimeEventType.HEARTBEAT, self._handle_heartbeat)
        self._subscribed = False

    def update(self, dt: float) -> None:
        """The soul system reacts to events; no per-frame work required yet."""
        return

    def take_soul_damage(self, entity: Entity, amount: int) -> bool:
        soul = self.world.get(entity, Soul)
        if soul is None:
            return False
        return self._consume_soul(soul, amount)

    def restore_soul(self, entity: Entity, amount: int) -> int:
        soul = self.world.get(entity, Soul)
        if soul is None:
            return 0
        return self._restore_soul(soul, amount)

    def restore_full(self, entity: Entity) -> None:
        soul = self.world.get(entity, Soul)
        if soul is None:
            return
        self._normalize_component(soul)
        soul.current_soul = soul.max_soul
        soul.depleted_announced = False

    def _handle_heartbeat(self, event: TimeEvent) -> None:
        if self._heartbeat_cost <= 0:
            return
        souls = self.world.get_component(Soul)
        for entity, soul in souls:
            if soul.max_soul <= 0:
                continue
            position = self.world.get(entity, Position)
            in_safe_zone = False
            if position is not None:
                in_safe_zone = self._is_position_in_safe_zone(float(position.x), float(position.y))
            if not should_drain_on_heartbeat(event, in_safe_zone=in_safe_zone):
                continue
            self._consume_soul(soul, self._heartbeat_cost)

    def _is_position_in_safe_zone(self, x: float, y: float) -> bool:
        target = (x, y)
        for _, zone_component, zone_position in self.world.view(SafeZoneComponent, Position):
            zone_origin = (float(zone_position.x), float(zone_position.y))
            if safe_zone_contains_position(
                zone_component,
                zone_origin,
                target,
                tile_size=self._tile_size,
            ):
                return True
        return False

    def _normalize_component(self, soul: Soul) -> None:
        soul.max_soul = int(max(0, soul.max_soul))
        if soul.current_soul is None:
            soul.current_soul = soul.max_soul
        soul.current_soul = int(max(0, min(int(soul.current_soul), soul.max_soul)))

    def _consume_soul(self, soul: Soul, amount: int) -> bool:
        spend = int(amount)
        if spend <= 0:
            return True
        self._normalize_component(soul)
        if soul.max_soul <= 0 or soul.current_soul < spend:
            self._announce_depleted(soul)
            return False
        soul.current_soul -= spend
        if soul.current_soul <= 0:
            soul.current_soul = 0
            self._announce_depleted(soul)
        else:
            soul.depleted_announced = False
        return True

    def _restore_soul(self, soul: Soul, amount: int) -> int:
        restore_amount = int(amount)
        if restore_amount <= 0:
            return 0
        self._normalize_component(soul)
        before = soul.current_soul
        soul.current_soul = min(soul.max_soul, soul.current_soul + restore_amount)
        if soul.current_soul > 0:
            soul.depleted_announced = False
        return soul.current_soul - before

    def _announce_depleted(self, soul: Soul) -> None:
        if soul.depleted_announced:
            return
        print("[Soul] Player is exhausted: no soul remaining.")
        soul.depleted_announced = True


__all__ = ["SoulSystem", "SoulCosts", "should_drain_on_heartbeat"]
