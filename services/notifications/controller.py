"""High-level controller coordinating notification UI and triggers."""

from __future__ import annotations

from typing import Tuple

import pygame

from services.progression import Progression
from .manager import NotificationManager
from .ui import (
    SystemButton,
    JournalPanel,
    JournalPanelResult,
    NotificationScreen,
    NotificationScreenResult,
    AchievementScreen,
    AchievementScreenResult,
    StatsScreen,
    StatsScreenResult,
    FormulaScreen,
    FormulaScreenResult,
)
from services.asset_loader.notification_assets import NotificationUIAssets


class NotificationController:
    """Coordinates notification manager with UI components."""

    def __init__(
        self,
        manager: NotificationManager,
        achievements_manager: NotificationManager,
        assets: NotificationUIAssets,
    ) -> None:
        self.manager = manager
        self.achievements_manager = achievements_manager
        self.assets = assets
        self.system_button = SystemButton(self.assets)
        self.journal_panel = JournalPanel(self.assets)
        self.notification_screen = NotificationScreen(self.assets)
        self.achievement_screen = AchievementScreen(self.assets)
        self.stats_screen = StatsScreen(self.assets)
        self.formula_screen = FormulaScreen(self.assets)
        # Ensure placeholder text is rendered
        self.notification_screen.set_entry(self.manager.current())
        self.achievement_screen.set_entry(self.achievements_manager.current())
        self.achievement_screen.hide()
        self.stats_screen.hide()
        self.formula_screen.hide()
        self._surface_size: Tuple[int, int] = (0, 0)
        self._progression: Progression | None = None
        self._formulas_library = None

    def set_progression(self, progression: Progression) -> None:
        self._progression = progression
        self.stats_screen.attach_progression(progression)
        # Formulas progression refresh happens via notifications system callbacks

    def set_formulas_library(self, library) -> None:
        self._formulas_library = library
        self.formula_screen.attach_library(library)

    def reposition(self, surface_size: Tuple[int, int]) -> None:
        """Update layout when the render surface size changes."""
        if surface_size == self._surface_size:
            return
        self._surface_size = surface_size
        self.system_button.reposition(surface_size)
        self.journal_panel.reposition(surface_size)
        self.notification_screen.reposition(surface_size)
        self.achievement_screen.reposition(surface_size)
        self.stats_screen.reposition(surface_size)
        self.formula_screen.reposition(surface_size)

    def handle_event(self, event) -> bool:
        """Process input events. Returns True if consumed."""
        consumed = False
        panel_toggled = False

        if self.system_button.handle_event(event):
            consumed = True
            if self.journal_panel.visible:
                self.journal_panel.hide()
                self.notification_screen.hide()
                self.achievement_screen.hide()
                self.stats_screen.hide()
                self.formula_screen.hide()
            else:
                self.stats_screen.hide()
                self.notification_screen.hide()
                self.achievement_screen.hide()
                self.formula_screen.hide()
                self.journal_panel.show()
            panel_toggled = True

        if self.journal_panel.visible and not panel_toggled:
            result = self.journal_panel.handle_event(event)
            if result == JournalPanelResult.STATS:
                consumed = True
                self.journal_panel.hide()
                self.notification_screen.hide()
                self.achievement_screen.hide()
                self.formula_screen.hide()
                if self._progression is not None:
                    self.stats_screen.refresh()
                self.stats_screen.show()
            elif result == JournalPanelResult.NOTIFICATIONS:
                consumed = True
                self.stats_screen.hide()
                self.achievement_screen.hide()
                self.formula_screen.hide()
                if not self.notification_screen.is_visible():
                    self.notification_screen.show()
                entry = self.manager.latest()
                self.notification_screen.set_entry(entry)
            elif result == JournalPanelResult.ACHIEVEMENTS:
                consumed = True
                self.stats_screen.hide()
                self.notification_screen.hide()
                self.formula_screen.hide()
                if not self.achievement_screen.is_visible():
                    self.achievement_screen.show()
                entry = self.achievements_manager.latest()
                self.achievement_screen.set_entry(entry)
            elif result == JournalPanelResult.FORMULAS:
                consumed = True
                self.journal_panel.hide()
                self.stats_screen.hide()
                self.notification_screen.hide()
                self.achievement_screen.hide()
                self.formula_screen.refresh()
                self.formula_screen.show()
            elif result != JournalPanelResult.NONE:
                consumed = True

        if self.stats_screen.is_visible():
            result = self.stats_screen.handle_event(event)
            if result == StatsScreenResult.CLOSE:
                consumed = True
                self.stats_screen.hide()
                self.journal_panel.show()

        if self.formula_screen.is_visible():
            result = self.formula_screen.handle_event(event)
            if result == FormulaScreenResult.CLOSE:
                consumed = True
                self.formula_screen.hide()
                self.journal_panel.show()

        if self.achievement_screen.is_visible():
            result = self.achievement_screen.handle_event(event)
            if result == AchievementScreenResult.PREVIOUS:
                consumed = True
                entry = self.achievements_manager.previous()
                self.achievement_screen.set_entry(entry)
            elif result == AchievementScreenResult.CURRENT:
                consumed = True
                entry = self.achievements_manager.latest()
                self.achievement_screen.set_entry(entry)
            elif result == AchievementScreenResult.CLOSE:
                consumed = True
                self.achievement_screen.hide()
                self.journal_panel.show()

        if self.notification_screen.is_visible():
            result = self.notification_screen.handle_event(event)
            if result == NotificationScreenResult.PREVIOUS:
                consumed = True
                entry = self.manager.previous()
                self.notification_screen.set_entry(entry)
            elif result == NotificationScreenResult.CURRENT:
                consumed = True
                entry = self.manager.latest()
                self.notification_screen.set_entry(entry)
            elif result == NotificationScreenResult.CLOSE:
                consumed = True
                self.notification_screen.hide()

        return consumed

    def update(self, dt: float) -> None:
        self.system_button.update(dt)
        self.journal_panel.update(dt)
        self.notification_screen.update(dt)
        self.achievement_screen.update(dt)
        self.stats_screen.update(dt)
        self.formula_screen.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self.system_button.draw(surface)
        self.journal_panel.draw(surface)
        self.notification_screen.draw(surface)
        self.achievement_screen.draw(surface)
        self.stats_screen.draw(surface)
        self.formula_screen.draw(surface)

    def on_history_updated(self) -> None:
        """Refresh current screen content after history changes."""
        current = self.manager.current()
        self.notification_screen.set_entry(current)

    def on_achievements_updated(self) -> None:
        """Refresh achievement screen content after history changes."""
        current = self.achievements_manager.current()
        self.achievement_screen.set_entry(current)

    def on_formulas_updated(self) -> None:
        """Refresh formula screen content after known recipes change."""
        if self.formula_screen.is_visible():
            self.formula_screen.refresh()


__all__ = ["NotificationController"]
