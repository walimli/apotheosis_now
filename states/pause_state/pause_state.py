import pygame

from services.audio_package import publish_audio_event


class PauseState:
    def __init__(self, game, display):
        self.game = game
        self.display = display
        self._time_paused = False

    @property
    def play_state(self):
        return self.game.states["play"]

    def _pause_time(self):
        self._reset_input_state()
        self.play_state.time_manager.pause()
        self._time_paused = True

    def _resume_time(self):
        self._reset_input_state()
        self.play_state.time_manager.resume()
        self._time_paused = False

    def handle_events(self, events):
        if not self._time_paused:
            self._pause_time()

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                publish_audio_event("ui.pause.toggle")
                self._resume_time()
                self.game.set_state("play")
                break

    def update(self, dt):
        if not self._time_paused:
            self._pause_time()

    def render(self, base_surface):
        self.play_state.render(base_surface)

    def _reset_input_state(self):
        input_bus = getattr(self.play_state, "input_bus", None)
        reset = getattr(input_bus, "full_reset", None)
        if callable(reset):
            reset()
