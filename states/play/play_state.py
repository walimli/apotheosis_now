"""Core PlayState implementation with ECS integration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame

from services.audio_package import AudioManager
from services.display.display_system import DisplayService
from services.time import TimeManager
from services.world_builder import WorldBuilder
from services.world_renderer import WorldRenderer
from services.asset_loader import load_tilesheet
from services.inputs import PlayInputBus, PlayInputContext, PlayAction
from services.ui.ui_manager import UIManager

# Import ECS components and systems
from ecs_core.worlds.world import World
from ecs_core.entities.entities import EntityManager
from ecs_core.components import Position, Controller, Camera2DComponent
from ecs_core.systems.controller import ControllerSystem
from ecs_core.systems.render import RenderSystem
from ecs_core.systems.animation.animation import AnimationSystem
from ecs_core.systems.movement import MovementSystem
from ecs_core.entities.player.player_core import spawn_player


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
        self._initialize_services()
        
        # Initialize ECS world and systems
        self._initialize_ecs()
        
        # Initialize player entity
        self._initialize_player()
        
        # Initialize input handling
        self._initialize_input()
        
        # Game state
        self.running = True
        
    def _initialize_services(self):
        """Initialize all game services."""
        # Load tiles and create world renderer
        self.tile_sheet = load_tilesheet(asset_root=self.project_root / "assets" / "tiles")
        
        # World builder (generates chunks)
        world_builder = WorldBuilder(seed=42, chunk_size=32)
        
        # World renderer (renders chunks, objects, entities)
        base_surface = self.display.get_base_surface()
        self.world_renderer = WorldRenderer(
            screen=base_surface,
            tile_sheet=self.tile_sheet,
            tile_size=64,
            chunk_size=32,
            world_builder=world_builder,
        )
        
        # Time manager (handles day/night cycle, time events)
        self.time_manager = TimeManager()

        font_path = str(self.project_root / "assets" / "ui" / "fonts" / "system.ttf")
        self.ui_manager = UIManager(
            self.display,
            font_path=font_path,
            time_manager=self.time_manager,
        )
        
    def _initialize_ecs(self):
        """Initialize the ECS world and systems."""
        self.ecs_world = World()
        self.entity_manager = EntityManager()
        # Create camera entity before wiring any systems
        self.camera_entity = self.entity_manager.create()
        camera_rect = pygame.Rect(0, 0, self.display.base_width, self.display.base_height)
        self.ecs_world.add(
            self.camera_entity,
            Camera2DComponent(
                rect=camera_rect,
                scale=1.0,
                scroll=(0.0, 0.0)
            )
        )

        # Initialize render system with a valid camera reference
        self.render_system = RenderSystem(
            self.display.get_base_surface(),
            self.camera_entity,
            self.ecs_world,
        )
        self._sync_camera_component_from_display()

        # Initialize controller system
        self.controller_system = ControllerSystem()
        self.controller_system.world = self.ecs_world
        self.controller_system.input_service = None  # Will be set in _initialize_input()

        # Animation system (handles sprite sheets + fallback circles)
        self.animation_system = AnimationSystem()
        self.animation_system.world = self.ecs_world

        self.movement_system = MovementSystem(self.ecs_world)

    def _initialize_player(self):
        """Initialize the player entity with proper ECS components."""
        self.player_entity = spawn_player(self.ecs_world, self.entity_manager)

        # Register player with ControllerSystem
        controller = self.ecs_world.get(self.player_entity, Controller)
        self.controller_system.register_entity(self.player_entity, controller)
        player_position = self.ecs_world.get(self.player_entity, Position)
        if player_position:
            self.display.update_camera(
                (player_position.x, player_position.y),
                0.0,
            )
            self._sync_camera_component_from_display()
        
    def _initialize_input(self):
        """Initialize input handling."""
        self.input_bus = PlayInputBus()
        self.input_context = PlayInputContext()
        
        # Wire input service to controller system
        self.controller_system.input_service = self.input_bus
        
        # Register for input events
        self.input_bus.subscribe(PlayAction.PAUSE_TOGGLE, self._handle_pause_toggle)
        # Quit is handled by pygame.QUIT events in handle_events()
        
    def handle_events(self, events):
        """Handle pygame events."""
        # Handle quit events
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.VIDEORESIZE:
                self.display.handle_resize(event)
                self._sync_camera_component_from_display()
                
        # Handle input events
        self.input_bus.process(events)
        
    def update(self, dt: float):
        """Update the game state."""
        if not self.running:
            return
            
        # Update time system
        time_events = self.time_manager.update(dt)
        
        # Update ECS systems
        self.controller_system.update(dt)
        self.animation_system.update(dt)
        # TODO: Add other ECS systems (speed, collision, etc.)
        self.movement_system.update(dt)
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
        self.animation_system.render(surface, camera_x, camera_y)
        
    def render_hud(self, screen: pygame.Surface):
        """Render HUD elements after the main world."""
        if hasattr(self, "ui_manager"):
            self.ui_manager.render_play_hud(
                screen,
                paused=(self.state_manager.current_state == "pause"),
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
        self.display.update_camera((player_position.x, player_position.y), dt)
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

