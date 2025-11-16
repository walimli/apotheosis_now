"""Core PlayState implementation with ECS integration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame

from services.audio_package import AudioManager
from services.display.display_system import DisplayService
from services.inputs import (
    PlayAction,
    HotbarInputAdapter,
    InventoryLockInputAdapter,
    LandscapingInputAdapter,
)
from services.landscaping.landscape_updater import bootstrap_land_systems
from states.play.bootstrap import build_services, create_ecs_runtime, wire_play_input
from states.play.player import PlayerBindings, spawn_player_runtime

# Import ECS components used by PlayState
from ecs_core.components import Camera2DComponent, Position


class PlayState:
    """Main game state that handles active gameplay with ECS integration."""

    def __init__(
        self,
        state_manager: object,
        display: DisplayService,
        audio_manager: AudioManager,
        project_root: Optional[Path] = None,
    ):
        """Initialize the play state with all required systems."""
        self.state_manager = state_manager
        self.display = display
        self.audio_manager = audio_manager
        self.project_root = project_root or Path(__file__).resolve().parents[2]

        # Initialize services
        services = build_services(self.display, self.audio_manager, self.project_root)
        self.tile_sheet = services.tile_sheet
        self.world_renderer = services.world_renderer
        self.monster_factory = services.monster_factory
        self.time_manager = services.time_manager
        self.ui_manager = services.ui_manager
        self.notifications = services.notifications
        self.ui = None

        ecs_runtime = create_ecs_runtime(self, self.display, services)
        self.ecs_world = ecs_runtime.world
        self.entity_manager = ecs_runtime.entity_manager
        self.camera_entity = ecs_runtime.camera_entity
        self.render_system = ecs_runtime.render_system
        self.controller_system = ecs_runtime.controller_system
        self.animation_system = ecs_runtime.animation_system
        self.speed_system = ecs_runtime.speed_system
        self.movement_system = ecs_runtime.movement_system
        self.soul_system = ecs_runtime.soul_system
        self.evolve_system = ecs_runtime.evolve_system
        self.aggressive_pathfinding_manager = ecs_runtime.aggressive_pathfinding_manager
        self.aggressive_ai_service = ecs_runtime.aggressive_ai_service
        self._sync_camera_component_from_display()

        self.landscaping_runtime = None
        self.landscaping_system = None
        self.landscape_updater = None
        self.landscaping_input_adapter: LandscapingInputAdapter | None = None

        player_runtime = spawn_player_runtime(
            play_state=self,
            ecs_runtime=ecs_runtime,
            display=self.display,
            ui_manager=self.ui_manager,
            notifications=self.notifications,
        )
        self.player_entity = player_runtime.player_entity
        self.player: PlayerBindings = player_runtime.bindings

        # Initialize landscaping (requires player bindings)
        self._initialize_landscaping()

        # Initialize input handling
        self._initialize_input()

        # Game state
        self.running = True
        self.hotbar_input_adapter: HotbarInputAdapter | None = None
        self.inventory_lock_input_adapter: InventoryLockInputAdapter | None = None

    def _initialize_landscaping(self) -> None:
        """Bootstrap the landscaping systems tied to the play state."""
        runtime = bootstrap_land_systems(self)
        self.landscaping_runtime = runtime
        self.landscaping_system = runtime.landscaping
        self.landscape_updater = runtime.updater

    def _initialize_input(self):
        """Initialize input handling."""
        input_runtime = wire_play_input(
            player_bindings=self.player,
            ui_components=self.ui,
            landscaping_system=self.landscaping_system,
            display=self.display,
        )
        self.input_bus = input_runtime.bus
        self.input_context = input_runtime.context
        self.hotbar_input_adapter = input_runtime.hotbar_adapter
        self.inventory_lock_input_adapter = input_runtime.inventory_lock_adapter
        self.landscaping_input_adapter = input_runtime.landscaping_adapter

        self.controller_system.input_service = self.input_bus

        self.input_bus.subscribe(PlayAction.PAUSE_TOGGLE, self._handle_pause_toggle)

    def handle_events(self, events):
        """Handle pygame events."""
        filtered_events = []
        for event in events:
            # Global window/state events take precedence
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.VIDEORESIZE:
                self.display.handle_resize(event)
                self._sync_camera_component_from_display()
                if hasattr(self, "notifications"):
                    surface_size = (
                        self.display.screen_width,
                        self.display.screen_height,
                    )
                    self.notifications.reposition(surface_size)
            # Allow notifications UI to intercept after global handling
            if hasattr(self, "notifications") and self.notifications.handle_event(
                event
            ):
                continue
            filtered_events.append(event)

        # Handle input events
        self.input_bus.process(filtered_events)

    def update(self, dt: float):
        """Update the game state."""
        if not self.running:
            return

        # Update time system
        time_events = self.time_manager.update(dt)
        if hasattr(self, "notifications"):
            self.notifications.handle_time_events(time_events)
            self.notifications.update(dt)

        # Update ECS systems
        self.controller_system.update(dt)
        if hasattr(self, "aggressive_pathfinding_manager"):
            self.aggressive_pathfinding_manager.update(dt)
        self.animation_system.update(dt)
        self.speed_system.update(dt)
        self.movement_system.update(dt)
        self.soul_system.update(dt)
        if hasattr(self, "evolve_system"):
            self.evolve_system.update(dt)
        if self.landscaping_system is not None:
            self.landscaping_system.update(dt)
        self._update_camera_tracking(dt)
        self._prepare_world_chunks()

    def render(self, surface: pygame.Surface):
        """Render the game world."""
        if not self.running:
            return

        # Get camera position and view rect
        camera_component = self.ecs_world.get(self.camera_entity, Camera2DComponent)
        if not camera_component:
            return

        camera_x = int(camera_component.rect.left)
        camera_y = int(camera_component.rect.top)

        # Render world (chunks, objects, entities)
        self.world_renderer.render_visible_chunks(
            camera_x=camera_x,
            camera_y=camera_y,
            camera=camera_component,
        )
        self.render_system.update(0.0)
        self.animation_system.render(surface, camera_x, camera_y)
        if self.landscaping_system is not None:
            self.landscaping_system.render(surface)

    def render_hud(self, screen: pygame.Surface):
        """Render HUD elements after the main world."""
        if hasattr(self, "ui_manager"):
            self.ui_manager.render_play_hud(
                screen,
                paused=(self.state_manager.current_state == "pause"),
                play_state=self,
            )

    def _handle_pause_toggle(self, action, state):
        """Switch to the pause state via the state manager."""
        if state:
            self.state_manager.set_state("pause")

    def _update_camera_tracking(self, dt: float) -> None:
        """Drive the display camera to follow the player."""
        if dt is None:
            return
        player_position = self.ecs_world.get(self.player_entity, Position)
        if not player_position:
            return
        target_x = (
            player_position.render_x
            if player_position.render_x is not None
            else float(player_position.x)
        )
        target_y = (
            player_position.render_y
            if player_position.render_y is not None
            else float(player_position.y)
        )
        self.display.update_camera((target_x, target_y), dt)
        self._sync_camera_component_from_display()

    def _sync_camera_component_from_display(self) -> None:
        """Mirror the display camera state into the ECS camera component."""
        if not hasattr(self, "camera_entity"):
            return
        camera_rect = self.display.get_camera_rect()
        if not camera_rect:
            return
        rect = camera_rect.copy()
        scale = self.display.get_camera_scale()
        self.ecs_world.add(
            self.camera_entity,
            Camera2DComponent(
                rect=rect,
                scale=scale,
                scroll=(rect.left, rect.top),
            ),
        )

    def _prepare_world_chunks(self) -> None:
        """Ensure visible chunks are available through the world renderer."""
        if not hasattr(self, "world_renderer"):
            return
        camera_rect = self.display.get_camera_rect()
        if camera_rect:
            self.world_renderer.ensure_chunks_for_camera(camera_rect)
