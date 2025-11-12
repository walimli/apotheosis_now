import pygame
import sys
from pathlib import Path

from services.audio_package import AudioEventListener, AudioManager, set_global_listener

# Corrected imports, relative to the project root
from services.display.display_system.service import DisplayService
from states.title_state.title_menu.title_state_manager import TitleStateManager
from states.play import PlayState
from states.progression_state.manager import ProgressionState
from states.pause_state.pause_state import PauseState


class StateManager:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("The Dark Lord of Crafting")
        self.display = DisplayService(initial_width=1200, initial_height=800)
        self.clock = pygame.time.Clock()
        self.current_state = "title"
        self.running = True
        self.project_root = Path(__file__).resolve().parents[1]
        registry_path = self.project_root / "services" / "audio_package" / "sound_registry.json"
        self.audio_manager = AudioManager(registry_path)
        self.audio_listener = AudioEventListener(self.audio_manager)
        set_global_listener(self.audio_listener)
        self.states = {}
        self._load_states()
        self.audio_listener.on_state_changed(self.current_state)

    def _load_states(self):
        self.states["title"] = TitleStateManager(self, self.display)
        self.states["play"] = PlayState(self, self.display, self.audio_manager, self.project_root)
        self.states["pause"] = PauseState(self, self.display)
        self.states["progression"] = ProgressionState(self, self.display)

    def set_state(self, state_name):
        if state_name in self.states:
            self.current_state = state_name
            self.audio_listener.on_state_changed(state_name)

    def quit(self):
        self.running = False

    def handle_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.quit()
                return
            elif event.type == pygame.VIDEORESIZE:
                self.display.handle_resize(event)

        self.states[self.current_state].handle_events(events)

    def update(self):
        dt = self.clock.tick(60) / 1000.0  # Delta time in seconds
        self.states[self.current_state].update(dt)

    def render(self):
        base_surface = self.display.get_base_surface()
        base_surface.fill((0, 0, 0))  # Clear base surface before state rendering
        self.states[self.current_state].render(base_surface)
        self.display.render()
        # Optional HUD overlay render (drawn at screen pixel scale, not doubled)
        state = self.states[self.current_state]
        if hasattr(state, "render_hud"):
            try:
                state.render_hud(self.display.screen)
            except Exception:
                # Fail-safe: do not crash render loop on HUD errors
                pass
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()

        pygame.quit()
        sys.exit()



