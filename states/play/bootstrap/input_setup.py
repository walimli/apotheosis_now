"""PlayState input wiring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.display.display_system import DisplayService
from services.inputs import (
    HotbarInputAdapter,
    InventoryLockInputAdapter,
    LandscapingInputAdapter,
    PlayInputBus,
    PlayInputContext,
)


@dataclass(frozen=True)
class InputRuntime:
    """Grouped input bus/context/adapters for PlayState."""

    bus: PlayInputBus
    context: PlayInputContext
    hotbar_adapter: HotbarInputAdapter
    inventory_lock_adapter: InventoryLockInputAdapter
    landscaping_adapter: Optional[LandscapingInputAdapter]


def wire_play_input(
    *,
    player_bindings: Any,
    ui_components: Any,
    landscaping_system: Any,
    display: DisplayService,
) -> InputRuntime:
    """
    Create the shared PlayInputBus/context and attach relevant adapters.

    Raises the same RuntimeErrors as the original PlayState wiring when required
    dependencies are missing.
    """
    if player_bindings is None:
        raise RuntimeError("Player bindings must exist before wiring input adapters")
    if ui_components is None:
        raise RuntimeError("UI components missing; cannot attach hotbar input adapters")

    inventory = getattr(player_bindings, "inventory", None)
    if inventory is None:
        raise RuntimeError("Player inventory missing; cannot attach hotbar adapter")

    lock_state = getattr(player_bindings, "lock_state", None)
    if lock_state is None:
        raise RuntimeError("Inventory lock state missing; cannot attach lock adapter")

    hotbar_ui = getattr(ui_components, "hotbar", None)
    if hotbar_ui is None:
        raise RuntimeError("Hotbar UI missing; cannot attach hotbar adapter")

    bus = PlayInputBus()
    context = PlayInputContext()
    context.inventory = inventory
    context.inventory_lock = lock_state
    context.hotbar_ui = hotbar_ui
    context.display = display
    context.camera = display
    context.landscaping_system = landscaping_system

    hotbar_adapter = HotbarInputAdapter(
        bus=bus,
        context=context,
        inventory=inventory,
        hotbar_ui=hotbar_ui,
    )
    hotbar_adapter.attach()

    inventory_lock_adapter = InventoryLockInputAdapter(
        bus=bus,
        context=context,
        lock_state=lock_state,
    )
    inventory_lock_adapter.attach()

    landscaping_adapter: Optional[LandscapingInputAdapter] = None
    if landscaping_system is not None:
        landscaping_adapter = LandscapingInputAdapter(
            bus=bus,
            context=context,
            system=landscaping_system,
        )
        landscaping_adapter.attach()

    return InputRuntime(
        bus=bus,
        context=context,
        hotbar_adapter=hotbar_adapter,
        inventory_lock_adapter=inventory_lock_adapter,
        landscaping_adapter=landscaping_adapter,
    )

