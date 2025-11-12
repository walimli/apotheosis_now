from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .actions import PlayAction
from .context import PlayInputContext
from .dispatcher import PlayInputBus
from .state import PlayInputState


@dataclass
class BaseInputAdapter:
    bus: PlayInputBus
    context: PlayInputContext

    def attach(self) -> None:
        """Register callbacks with the bus."""
        return

    def crafting_active(self) -> bool:
        if self.context is None:
            return False
        system = getattr(self.context, "crafting_system", None)
        return bool(getattr(system, "active", False)) if system is not None else False

    def dialogue_active(self) -> bool:
        if self.context is None:
            return False
        dialogue = getattr(self.context, "dialogue_manager", None)
        return (
            bool(getattr(dialogue, "is_active", False))
            if dialogue is not None
            else False
        )


@dataclass
class PlayerInputAdapter(BaseInputAdapter):
    controller: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.MOVE, self._on_move)
        self.bus.subscribe(PlayAction.INTERACT_PRIMARY, self._on_interact)

    def _on_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.MOVE:
            return
        dx, dy = state.get_axis(PlayAction.MOVE)
        self.controller.set_move_input(dx, dy)

    def _on_interact(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.INTERACT_PRIMARY:
            return
        button = state.buttons.get(PlayAction.INTERACT_PRIMARY)
        if button and button.pressed:
            self.controller.handle_interact()


@dataclass
class LandscapingInputAdapter(BaseInputAdapter):
    system: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        if self.crafting_active():
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if button and button.pressed:
            self.system.handle_use_inventory()

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE:
            return
        if self.crafting_active():
            return
        camera = self.context.camera
        self.system.handle_cursor_move(state.cursor_pos, camera)


@dataclass
class FarmingInputAdapter(BaseInputAdapter):
    system: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        if self.crafting_active():
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if button and button.pressed:
            self.system.handle_use_inventory()

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE:
            return
        if self.crafting_active():
            return
        camera = self.context.camera
        self.system.handle_cursor_move(state.cursor_pos, camera)


@dataclass
class PlaceablesInputAdapter(BaseInputAdapter):
    manager: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)
        self.bus.subscribe(PlayAction.VARIANT_CYCLE, self._on_variant_cycle)
        self.bus.subscribe(PlayAction.PILL_ACTIVATE, self._on_pill_activate)

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE:
            return
        if self.crafting_active():
            return
        camera = self.context.camera
        self.manager.handle_cursor_move(state.cursor_pos, camera)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY:
            return
        if self.crafting_active():
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if button and button.pressed:
            camera = self.context.camera
            self.manager.handle_use_inventory(camera)

    def _on_variant_cycle(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.VARIANT_CYCLE:
            return
        if self.crafting_active():
            return
        button = state.buttons.get(PlayAction.VARIANT_CYCLE)
        if button and button.pressed:
            self.manager.handle_variant_cycle()

    def _on_pill_activate(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.PILL_ACTIVATE:
            return
        if self.crafting_active():
            return
        button = state.buttons.get(PlayAction.PILL_ACTIVATE)
        if button and button.pressed:
            self.manager.use_active_pill()


@dataclass
class InteractiblesInputAdapter(BaseInputAdapter):
    manager: Any

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.INTERACT_PRIMARY, self._on_interact)

    def _on_interact(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.INTERACT_PRIMARY:
            return
        if self.crafting_active() or self.dialogue_active():
            return
        button = state.buttons.get(PlayAction.INTERACT_PRIMARY)
        if not (button and button.pressed):
            return
        self.manager.trigger()


@dataclass
class CombatInputAdapter(BaseInputAdapter):
    system: Any | None = None

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.USE_INVENTORY, self._on_use_inventory)
        self.bus.subscribe(PlayAction.CURSOR_MOVE, self._on_cursor_move)

    def _on_cursor_move(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.CURSOR_MOVE or self.system is None:
            return
        handler = getattr(self.system, "handle_cursor_move", None)
        if callable(handler):
            handler(state.cursor_pos)

    def _on_use_inventory(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.USE_INVENTORY or self.system is None:
            return
        button = state.buttons.get(PlayAction.USE_INVENTORY)
        if not (button and button.pressed):
            return
        handler = getattr(self.system, "handle_primary_use", None)
        if callable(handler):
            handler(state)


@dataclass
class InventoryLockInputAdapter(BaseInputAdapter):
    lock_state: Any | None = None

    def attach(self) -> None:
        self.bus.subscribe(PlayAction.INVENTORY_LOCK_TOGGLE, self._on_toggle)

    def _on_toggle(self, action: PlayAction, state: PlayInputState) -> None:
        if action != PlayAction.INVENTORY_LOCK_TOGGLE:
            return
        if self.lock_state is None:
            return
        button = state.buttons.get(PlayAction.INVENTORY_LOCK_TOGGLE)
        if button and button.pressed:
            self.lock_state.toggle()
