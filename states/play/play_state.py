"""Core PlayState implementation with ECS integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pygame

from services.audio_package import AudioManager
from services.display.display_system import DisplayService
from services.inventory import Inventory
from services.inventory.factory import create_player_inventory
from services.inventory.lock_state import InventoryLockState
from services.progression import Progression
from services.time import TimeManager
from services.world_builder import WorldBuilder
from services.world_renderer import WorldRenderer
from services.asset_loader import load_tilesheet
from services.inputs import (
    PlayInputBus,
    PlayInputContext,
    PlayAction,
    HotbarInputAdapter,
    InventoryLockInputAdapter,
    LandscapingInputAdapter,
)
from services.notifications import NotificationService
from services.ui.ui_manager import UIManager
from services.landscaping.landscape_updater import bootstrap_land_systems

# Import ECS components and systems
from ecs_core.worlds.world import World
from ecs_core.entities.entities import EntityManager
from ecs_core.components import (
    Camera2DComponent,
    Controller,
    Health,
    Position,
    Soul,
)
from ecs_core.systems.controller import ControllerSystem
from ecs_core.systems.render import RenderSystem
from ecs_core.systems.animation.animation import AnimationSystem
from ecs_core.systems.movement import MovementSystem
from ecs_core.systems.soul.soul import SoulSystem
from ecs_core.entities.player.player_core import spawn_player


class _HealthView:
    """Adapter exposing legacy health attributes for UI code."""

    def __init__(self, component: Optional[Health]) -> None:
        self._component = component

    @property
    def max_hp(self) -> int:
        return int(self._value("max_health", fallback="max_hp"))

    @property
    def current_hp(self) -> int:
        return int(self._value("current_health", fallback="current_hp"))

    def _value(self, primary: str, *, fallback: Optional[str] = None) -> float:
        component = self._component
        if component is None:
            return 0.0
        if hasattr(component, primary):
            return getattr(component, primary)
        if fallback and hasattr(component, fallback):
            return getattr(component, fallback)
        return 0.0


@dataclass
class _PlayerModelBindings:
    health: _HealthView
    soul: Soul | None
    progression: Progression


@dataclass
class _PlayerBindings:
    inventory: Inventory
    lock_state: InventoryLockState
    model: _PlayerModelBindings


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

        self.landscaping_runtime = None
        self.landscaping_system = None
        self.landscape_updater = None
        self.landscaping_input_adapter: LandscapingInputAdapter | None = None

        # Initialize player entity
        self._initialize_player()

        # Initialize landscaping (requires player bindings)
        self._initialize_landscaping()

        # Initialize input handling
        self._initialize_input()

        # Game state
        self.running = True
        self.hotbar_input_adapter: HotbarInputAdapter | None = None
        self.inventory_lock_input_adapter: InventoryLockInputAdapter | None = None
        self._inventory_adapters_attached = False

    def _initialize_services(self):
        """Initialize all game services."""
        # Load tiles and create world renderer
        self.tile_sheet = load_tilesheet(
            asset_root=self.project_root / "assets" / "tiles"
        )

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
        self.ui = None
        self.notifications = NotificationService(
            project_root=self.project_root,
            display=self.display,
        )

    def _initialize_ecs(self):
        """Initialize the ECS world and systems."""
        self.ecs_world = World()
        self.entity_manager = EntityManager()
        # Create camera entity before wiring any systems
        self.camera_entity = self.entity_manager.create()
        camera_rect = pygame.Rect(
            0, 0, self.display.base_width, self.display.base_height
        )
        self.ecs_world.add(
            self.camera_entity,
            Camera2DComponent(rect=camera_rect, scale=1.0, scroll=(0.0, 0.0)),
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
        self.controller_system.input_service = (
            None  # Will be set in _initialize_input()
        )

        # Animation system (handles sprite sheets + fallback circles)
        self.animation_system = AnimationSystem()
        self.animation_system.world = self.ecs_world

        self.movement_system = MovementSystem(self.ecs_world)
        self.soul_system = SoulSystem(
            self.ecs_world,
            self.time_manager,
            tile_size=getattr(self.world_renderer, "tile_size", 64),
        )

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
        self._initialize_player_bindings()

    def _initialize_landscaping(self) -> None:
        """Bootstrap the landscaping systems tied to the play state."""
        runtime = bootstrap_land_systems(self)
        self.landscaping_runtime = runtime
        self.landscaping_system = runtime.landscaping
        self.landscape_updater = runtime.updater

    def _initialize_input(self):
        """Initialize input handling."""
        self.input_bus = PlayInputBus()
        self.input_context = PlayInputContext()
        self._refresh_input_context()
        self._attach_inventory_input_adapters()
        self._attach_landscaping_input_adapter()

        # Wire input service to controller system
        self.controller_system.input_service = self.input_bus

        # Register for input events
        self.input_bus.subscribe(PlayAction.PAUSE_TOGGLE, self._handle_pause_toggle)
        # Quit is handled by pygame.QUIT events in handle_events()

    def _refresh_input_context(self) -> None:
        """Populate shared input context with the live play-state dependencies."""
        context = getattr(self, "input_context", None)
        if context is None:
            return
        player = getattr(self, "player", None)
        ui_components = getattr(self, "ui", None)
        context.inventory = getattr(player, "inventory", None) if player else None
        context.inventory_lock = (
            getattr(player, "lock_state", None) if player else None
        )
        context.hotbar_ui = (
            getattr(ui_components, "hotbar", None) if ui_components else None
        )
        context.display = self.display
        context.camera = self.display
        context.landscaping_system = getattr(self, "landscaping_system", None)

    def _attach_inventory_input_adapters(self) -> None:
        """Wire hotbar + lock-state input adapters into the play input bus."""
        if getattr(self, "_inventory_adapters_attached", False):
            return
        if not getattr(self, "player", None):
            raise RuntimeError("Player bindings must exist before wiring input adapters")
        if not getattr(self, "ui", None):
            raise RuntimeError("UI components missing; cannot attach hotbar input adapters")
        inventory = getattr(self.player, "inventory", None)
        if inventory is None:
            raise RuntimeError("Player inventory missing; cannot attach hotbar adapter")
        lock_state = getattr(self.player, "lock_state", None)
        if lock_state is None:
            raise RuntimeError("Inventory lock state missing; cannot attach lock adapter")
        hotbar_ui = getattr(self.ui, "hotbar", None)
        if hotbar_ui is None:
            raise RuntimeError("Hotbar UI missing; cannot attach hotbar adapter")
        self.hotbar_input_adapter = HotbarInputAdapter(
            bus=self.input_bus,
            context=self.input_context,
            inventory=inventory,
            hotbar_ui=hotbar_ui,
        )
        self.hotbar_input_adapter.attach()
        self.inventory_lock_input_adapter = InventoryLockInputAdapter(
            bus=self.input_bus,
            context=self.input_context,
            lock_state=lock_state,
        )
        self.inventory_lock_input_adapter.attach()
        self._inventory_adapters_attached = True

    def _attach_landscaping_input_adapter(self) -> None:
        system = getattr(self, "landscaping_system", None)
        if system is None:
            return
        self.landscaping_input_adapter = LandscapingInputAdapter(
            bus=self.input_bus,
            context=self.input_context,
            system=system,
        )
        self.landscaping_input_adapter.attach()

    def _initialize_player_bindings(self) -> None:
        """Create player bindings for UI + progression."""
        inventory = create_player_inventory()
        lock_state = InventoryLockState()
        health_component = self.ecs_world.get(self.player_entity, Health)
        soul_component = self.ecs_world.get(self.player_entity, Soul)
        progression = Progression()
        model = _PlayerModelBindings(
            health=_HealthView(health_component),
            soul=soul_component,
            progression=progression,
        )
        self.player = _PlayerBindings(
            inventory=inventory,
            lock_state=lock_state,
            model=model,
        )
        self.ui_manager.attach_play_state(
            self,
            player=self.player,
            lock_state=lock_state,
        )
        if hasattr(self, "notifications"):
            self.notifications.attach_progression(progression)
        self._refresh_input_context()

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
            if hasattr(self, "notifications") and self.notifications.handle_event(event):
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
        self.animation_system.update(dt)
        # TODO: Add other ECS systems (speed, collision, etc.)
        self.movement_system.update(dt)
        self.soul_system.update(dt)
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
