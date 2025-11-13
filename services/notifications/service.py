"""High-level service wrapper that wires notification managers into gameplay."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import json

import pygame

from services.display.display_system import DisplayService
from services.notifications.controller import NotificationController
from services.notifications.manager import NotificationManager
from services.asset_loader.notification_assets import NotificationUIAssets
from services.progression import Progression
from services.progression.formulas import FormulasLibrary, _load_recipes
from services.time.time_events import TimeEvent, TimeEventType


class NotificationService:
    """Owns notification UI, data managers, and trigger routing."""

    _TIME_EVENT_MAP = {
        TimeEventType.DAWN_STARTED: "time.dawn_started",
        TimeEventType.DAY_STARTED: "time.day_started",
        TimeEventType.NOON_REACHED: "time.noon_reached",
        TimeEventType.DUSK_STARTED: "time.dusk_started",
        TimeEventType.NIGHT_STARTED: "time.night_started",
        TimeEventType.MIDNIGHT_REACHED: "time.midnight_reached",
        TimeEventType.HEARTBEAT: "time.heartbeat",
    }

    def __init__(self, *, project_root: Path, display: DisplayService) -> None:
        self._project_root = project_root
        self._display = display
        self._assets = NotificationUIAssets()
        messages_root = project_root / "data" / "messages"
        notifications_path = messages_root / "notifications"
        achievements_path = messages_root / "achievements"
        self.manager = NotificationManager(notifications_path)
        self.achievements_manager = NotificationManager(achievements_path)
        self.controller = NotificationController(
            self.manager,
            self.achievements_manager,
            self._assets,
        )
        self._formulas = self._build_formulas_library(project_root)
        if self._formulas is not None:
            self.controller.set_formulas_library(self._formulas)
        self._progression: Progression | None = None
        self._formula_callback_attached = False
        self.controller.reposition(self._surface_size())
        # Prime baseline content so opening the screen on a fresh run works.
        self.fire_trigger("new_game_start")

    # --- Public wiring -------------------------------------------------
    def attach_progression(self, progression: Progression) -> None:
        """Bind progression + formulas to the stats/formulas screens."""
        self._progression = progression
        self.controller.set_progression(progression)
        if self._formulas is not None:
            self._sync_formulas_to_progression()
            if not self._formula_callback_attached:
                progression.set_on_formula_leveled(self._on_formula_leveled)
                self._formula_callback_attached = True

    def handle_event(self, event) -> bool:
        """Return True if the notification UI consumed the event."""
        return self.controller.handle_event(event)

    def update(self, dt: float) -> None:
        self.controller.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.controller.draw(surface)

    def reposition(self, surface_size: tuple[int, int]) -> None:
        self.controller.reposition(surface_size)

    def handle_time_events(self, events: Iterable[TimeEvent]) -> None:
        for event in events:
            trigger = self._TIME_EVENT_MAP.get(event.event_type)
            if trigger:
                self.fire_trigger(trigger)
            if event.event_type == TimeEventType.DAY_STARTED:
                day_trigger = f"time.day_{event.game_day}_start"
                self.fire_trigger(day_trigger)

    def fire_trigger(self, trigger: str, payload: Optional[Dict] = None) -> None:
        """Publish a trigger to both history streams and refresh UI state."""
        fired = self.manager.trigger(trigger, payload)
        if fired:
            self.controller.on_history_updated()
        achievements = self.achievements_manager.trigger(trigger, payload)
        if achievements:
            self.controller.on_achievements_updated()

    # --- Internals -----------------------------------------------------
    def _surface_size(self) -> tuple[int, int]:
        return (self._display.screen_width, self._display.screen_height)

    def _build_formulas_library(self, project_root: Path) -> FormulasLibrary | None:
        recipes_path = project_root / "data" / "formulas" / "crafting_recipes.json"
        inventory_root = project_root / "data" / "inventory"
        if not recipes_path.exists():
            return None
        recipes = _load_recipes(recipes_path)
        names = self._load_inventory_names(inventory_root)
        return FormulasLibrary(recipes, names)

    def _load_inventory_names(self, inventory_root: Path) -> Dict[str, str]:
        names: Dict[str, str] = {}
        if not inventory_root.exists():
            return names
        for path in inventory_root.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                for_inventory = data.get("for_inventory")
                if isinstance(for_inventory, dict):
                    for key, node in for_inventory.items():
                        name = self._coerce_display_name(node)
                        if name:
                            names[str(key)] = name
                items = data.get("inventory_items")
                if isinstance(items, list):
                    for node in items:
                        if not isinstance(node, dict):
                            continue
                        key = node.get("id")
                        name = self._coerce_display_name(node)
                        if key and name:
                            names[str(key)] = name
        return names

    @staticmethod
    def _coerce_display_name(node) -> Optional[str]:
        if not isinstance(node, dict):
            return None
        display = node.get("display_name")
        if isinstance(display, str) and display.strip():
            return display.strip()
        return None

    def _on_formula_leveled(self, level: int) -> None:
        del level  # level handled implicitly via sync
        self._sync_formulas_to_progression()

    def _sync_formulas_to_progression(self) -> None:
        if self._progression is None or self._formulas is None:
            return
        level = self._progression.get_upgrade_level("formula")
        self._formulas.sync_to_level(level)
        self.controller.on_formulas_updated()


__all__ = ["NotificationService"]
