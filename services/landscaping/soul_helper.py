from __future__ import annotations

from typing import Optional, Tuple
import types

from ecs_core.systems.soul.soul import SoulSystem, SoulCosts, Soul
from ecs_core.systems.soul.safe_zone import SafeZoneComponent


def attach_soul_hooks(
    system,
    soul: Optional[Soul],
    *,
    harvest_cost: Optional[int] = None,
    placement_cost: Optional[int] = None,
) -> None:
    """Inject soul gating into landscaping without touching manager internals."""
    if soul is None:
        return
    if getattr(system, "_soul_hooks_installed", False):
        return

    harvest = SoulCosts.LANDSCAPE_HARVEST if harvest_cost is None else int(harvest_cost)
    placement = (
        SoulCosts.LANDSCAPE_PLACE if placement_cost is None else int(placement_cost)
    )

    original_harvest = getattr(system, "_perform_harvest", None)
    original_notify = getattr(system, "_notify_tile_harvest", None)
    original_place = getattr(system, "_perform_placement", None)

    if callable(original_harvest) and callable(original_notify):

        def _guarded_harvest(self, tile_coords):
            if harvest > 0 and not soul.can_spend(harvest):
                soul.announce_blocked()
                return
            return original_harvest(tile_coords)

        def _notify(self, tile_coords, previous_tile_code, was_moss):
            result = original_notify(tile_coords, previous_tile_code, was_moss)
            if harvest > 0:
                soul.consume(harvest)
            return result

        system._perform_harvest = types.MethodType(_guarded_harvest, system)
        system._notify_tile_harvest = types.MethodType(_notify, system)

    if callable(original_place):

        def _guarded_place(self, tile_coords: Tuple[int, int]):
            if placement > 0 and not soul.can_spend(placement):
                soul.announce_blocked()
                return
            before = self._updater.get_tile_value(tile_coords[0], tile_coords[1])
            original_place(tile_coords)
            if placement <= 0:
                return
            after = self._updater.get_tile_value(tile_coords[0], tile_coords[1])
            void_code = getattr(self, "VOID_TILE_CODE", 0)
            if before == void_code and after != void_code:
                soul.consume(placement)

        system._perform_placement = types.MethodType(_guarded_place, system)

    setattr(system, "_soul_hooks_installed", True)


__all__ = ["attach_soul_hooks"]
