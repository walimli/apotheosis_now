"""Core PlayState implementation with ECS integration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame
import numpy as np

from services.audio_package import AudioManager
from services.display.display_system import DisplayService
from services.time import TimeManager, GameTimeOverlay
from services.world_builder import WorldBuilder
from services.world_renderer import WorldRenderer
from services.asset_loader.tiles import load_tilesheet
from services.inputs import PlayInputBus, PlayInputContext, PlayAction

# Import ECS components and systems
from systems.ecs_core import (
    World,
    EntityManager,
    Entity,
    Position,
    Velocity,
    Renderable,
    PlayerControlled,
    Camera2DComponent,
)
from ecs_core.systems.render import RenderSystem


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
        self.paused = False
        
    def _initialize_services(self):
        """Initialize all game services."""
        # Load tiles and create world renderer
        try:
            self.tile_sheet = load_tilesheet(asset_root=self.project_root / "assets" / "tiles")
        except FileNotFoundError:
            # Create a fallback tilesheet if assets are missing
            print("Warning: Could not load tilesheet, using placeholder")
            self.tile_sheet = self._create_placeholder_tilesheet()
        
        # World builder (generates chunks)
        self.world_builder = WorldBuilder(seed=42, chunk_size=32)
        
        # World renderer (renders chunks, objects, entities)
        base_surface = self.display.get_base_surface()
        self.world_renderer = WorldRenderer(
            screen=base_surface,
            tile_sheet=self.tile_sheet,
            tile_size=64,
            chunk_size=32,
        )
        
        # Time manager (handles day/night cycle, time events)
        self.time_manager = TimeManager()
        
        # Time display overlay
        self.time_display = GameTimeOverlay(
            clock=self.time_manager.clock,
            label="Game Time",
            pos=(30, 30),
            use_12_hour=True
        )
        
    def _initialize_ecs(self):
        """Initialize the ECS world and systems."""
        self.ecs_world = World()
        self.entity_manager = EntityManager()
        
        # Initialize render system
        self.render_system = RenderSystem(self.display.get_base_surface(), (0, 0), self.ecs_world)
        
        # Create camera entity
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
        
        # Store chunk data
        self.world_chunks: Dict[Tuple[int, int], np.ndarray] = {}
        self.world_objects: Dict[Tuple[int, int], list] = {}
        self.world_entities: list = []
        
    def _initialize_player(self):
        """Initialize the player entity with ECS components."""
        # Create player entity
        self.player_entity = self.entity_manager.create()
        
        # Add basic components
        self.ecs_world.add(self.player_entity, Position(x=400.0, y=300.0))
        self.ecs_world.add(self.player_entity, Velocity(vx=0.0, vy=0.0))
        self.ecs_world.add(self.player_entity, PlayerControlled())
        
        # Camera follows player
        self.camera_follow_player = True
        
    def _initialize_input(self):
        """Initialize input handling."""
        self.input_bus = PlayInputBus()
        self.input_context = PlayInputContext()
        
        # Register for input events
        self.input_bus.subscribe(PlayAction.PAUSE_TOGGLE, self._toggle_pause)
        # Quit is handled by pygame.QUIT events in handle_events()
        
    def _create_placeholder_tilesheet(self):
        """Create a fallback tilesheet when assets are missing."""
        # This is a simple placeholder - in a real implementation you'd handle this more gracefully
        from dataclasses import dataclass
        import pygame
        
        @dataclass(frozen=True)
        class PlaceholderTileSheet:
            tiles: list
            tile_size: int = 64
            
            def get(self, row: int, col: int) -> pygame.Surface:
                if row < len(self.tiles) and col < len(self.tiles[row]):
                    return self.tiles[row][col]
                # Return a placeholder surface
                surface = pygame.Surface((self.tile_size, self.tile_size))
                surface.fill((100, 100, 100))
                return surface
                
            @property
            def rows(self) -> int:
                return len(self.tiles)
                
            @property
            def cols(self) -> int:
                return len(self.tiles[0]) if self.tiles else 0
        
        # Create a simple 5x10 grid of colored squares
        tiles = []
        for row in range(5):
            row_tiles = []
            for col in range(10):
                surface = pygame.Surface((64, 64))
                # Create different colors for different tiles
                color = (50 + row * 30, col * 20, 100 + row * 10)
                surface.fill(color)
                row_tiles.append(surface)
            tiles.append(row_tiles)
        
        return PlaceholderTileSheet(tiles=tiles, tile_size=64)
        
    def handle_events(self, events):
        """Handle pygame events."""
        # Handle quit events
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.VIDEORESIZE:
                self.display.handle_resize(event)
                # Update camera rect for new screen size
                self._update_camera_rect()
                
        # Handle input events
        self.input_bus.process(events)
        
    def update(self, dt: float):
        """Update the game state."""
        if not self.running or self.paused:
            return
            
        # Update time system
        time_events = self.time_manager.update(dt)
        
        # Update camera to follow player
        if self.camera_follow_player:
            self._update_camera_follow()
            
        # Generate world around camera position
        self._generate_visible_chunks()
        
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
            chunks=self.world_chunks,
            objects=self.world_objects,
            camera_x=camera_x,
            camera_y=camera_y,
            entities=self.world_entities,
        )
        
    def render_hud(self, screen: pygame.Surface):
        """Render HUD elements after the main world."""
        # Simple HUD for now
        font = self.display.get_scaled_font(
            str(self.project_root / "assets" / "ui" / "fonts" / "system.ttf"),
            16
        )
        
        # Draw time display overlay
        if hasattr(self, 'time_display'):
            self.time_display.draw(screen)
            
        # Draw pause indicator
        if self.paused:
            pause_text = "PAUSED"
            pause_surface = font.render(pause_text, True, (255, 255, 0))
            text_rect = pause_surface.get_rect(center=screen.get_rect().center)
            screen.blit(pause_surface, text_rect)
            
    def _toggle_pause(self, action, state):
        """Toggle pause state."""
        self.paused = not self.paused
        if self.paused:
            self.time_manager.pause()
        else:
            self.time_manager.resume()
            
    def _update_camera_rect(self):
        """Update camera rect for new display size."""
        camera_component = self.ecs_world.get(self.camera_entity, Camera2DComponent)
        if camera_component:
            new_rect = pygame.Rect(
                camera_component.rect.left,
                camera_component.rect.top,
                self.display.base_width,
                self.display.base_height
            )
            self.ecs_world.add(
                self.camera_entity,
                Camera2DComponent(
                    rect=new_rect,
                    scale=camera_component.scale,
                    scroll=camera_component.scroll
                )
            )
            
    def _update_camera_follow(self):
        """Update camera to follow player position."""
        camera_component = self.ecs_world.get(self.camera_entity, Camera2DComponent)
        player_position = self.ecs_world.get(self.player_entity, Position)
        
        if camera_component and player_position:
            # Center camera on player
            target_x = player_position.x - (camera_component.rect.width / 2)
            target_y = player_position.y - (camera_component.rect.height / 2)
            
            # Create new rect with updated position
            new_rect = pygame.Rect(
                target_x,
                target_y,
                camera_component.rect.width,
                camera_component.rect.height
            )
            
            self.ecs_world.add(
                self.camera_entity,
                Camera2DComponent(
                    rect=new_rect,
                    scale=camera_component.scale,
                    scroll=(target_x, target_y)
                )
            )
            
    def _generate_visible_chunks(self):
        """Generate world chunks around the camera position."""
        if not hasattr(self, 'world_renderer'):
            return
            
        camera_component = self.ecs_world.get(self.camera_entity, Camera2DComponent)
        if not camera_component:
            return
            
        # Get visible chunk range (simple 3x3 around player)
        camera_x = camera_component.rect.left
        camera_y = camera_component.rect.top
        chunk_size = self.world_renderer.chunk_size * self.world_renderer.tile_size
        
        center_chunk_x = int(camera_x // chunk_size)
        center_chunk_y = int(camera_y // chunk_size)
        
        # Generate chunks in 3x3 area around camera
        for chunk_x in range(center_chunk_x - 1, center_chunk_x + 2):
            for chunk_y in range(center_chunk_y - 1, center_chunk_y + 2):
                chunk_key = (chunk_x, chunk_y)
                
                if chunk_key not in self.world_chunks:
                    try:
                        # Generate chunk using world builder
                        tiles, objects = self.world_builder.generate_chunk(chunk_x, chunk_y)
                        self.world_chunks[chunk_key] = tiles
                        self.world_objects[chunk_key] = objects
                    except Exception as e:
                        print(f"Error generating chunk {chunk_key}: {e}")
                        # Create empty chunk as fallback
                        self.world_chunks[chunk_key] = None
                        self.world_objects[chunk_key] = []