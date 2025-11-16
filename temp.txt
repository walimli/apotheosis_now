"""Service responsible for spawning non-player entities from spawn rules."""

from __future__ import annotations

import random
from pathlib import Path
import importlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from constants import CHUNK_SIZE_TILES, TILE_SIZE, TILE_CODE_VOID
from ecs_core.components import Position
from ecs_core.components.entity_classes import Player
from ecs_core.entities.entities import EntityManager, Entity
from .evolve_registry import evolvable_registry
from ecs_core.worlds.world import World
from services.time.time_events import TimeEvent, TimeEventType

from .placement import (
    TileCoord,
    choose_positions,
    eligible_coordinates,
    find_regions,
    filter_by_player_range,
    tile_is_eligible,
)
from .spawn_config import SpawnConfigLoader, SpawnRule

ChunkKey = Tuple[int, int]  # (chunk_x, chunk_y)


class MonsterFactoryService:
    """Loads spawn configs and instantiates monsters on configured events."""

    WORLD_START_EVENT = "world_start"

    def __init__(
        self,
        *,
        project_root: Optional[Path] = None,
        chunk_size: int = CHUNK_SIZE_TILES,
        tile_size: int = TILE_SIZE,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._project_root = Path(project_root or Path(__file__).resolve().parents[2])
        self._data_root = (self._project_root / "data" / "entities").resolve()

        self._chunk_size = int(chunk_size)
        self._tile_size = int(tile_size)
        self._rng = rng or random.Random()

        self._world: Optional[World] = None
        self._entity_manager: Optional[EntityManager] = None
        self._time_manager = None
        self._time_events_bound: set[TimeEventType] = set()
        self._chunks: Dict[ChunkKey, Tuple[np.ndarray, int, int]] = {}

        self._config_loader = SpawnConfigLoader(self._data_root)
        self._pending_events: List[Tuple[str, Dict[str, Any]]] = []
        self._ensure_entity_factories_loaded()

    # --- Public wiring -------------------------------------------------
    def bind_world(self, world: World, entity_manager: EntityManager) -> None:
        self._world = world
        self._entity_manager = entity_manager
        if self._pending_events:
            queued = list(self._pending_events)
            self._pending_events.clear()
            for event_name, context in queued:
                self._dispatch_event(event_name, context)

    def attach_time_manager(
        self,
        time_manager,
        event_types: Optional[Iterable[TimeEventType]] = None,
    ) -> None:
        """Subscribe to requested time events. Defaults to all if unspecified."""
        self._time_manager = time_manager
        events = list(event_types) if event_types else list(TimeEventType)
        for event_type in events:
            if event_type in self._time_events_bound:
                continue
            time_manager.subscribe_to_event(event_type, self._handle_time_event)
            self._time_events_bound.add(event_type)

    def handle_chunk_created(
        self,
        key: ChunkKey,
        tiles: np.ndarray,
        chunk_size: int,
        tile_size: int,
    ) -> None:
        """Entry point for world renderer chunk notifications."""
        self._chunks[key] = (np.array(tiles, copy=True), chunk_size, tile_size)
        context = {
            "chunk": key,
            "tiles": tiles,
            "chunk_size": chunk_size,
            "tile_size": tile_size,
        }
        self._process_event(self.WORLD_START_EVENT, context)

    def emit_event(self, event_name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Allow other systems to trigger factory events (e.g., planting)."""
        self._process_event(event_name, payload or {})

    # --- Event routing -------------------------------------------------
    def _handle_time_event(self, event: TimeEvent) -> None:
        event_name = event.event_type.name.lower()
        context = {"time_event": event}
        self._process_event(event_name, context)

    def _process_event(self, event_name: str, context: Dict[str, Any]) -> None:
        norm_event = self._normalize_event_name(event_name)
        if not self._world or not self._entity_manager:
            self._pending_events.append((norm_event, context))
            return
        if "chunk" in context and "tiles" in context:
            self._dispatch_event(norm_event, context)
            return
        if not self._chunks:
            return
        for chunk_key, (tiles, chunk_size, tile_size) in self._chunks.items():
            chunk_context = dict(context)
            chunk_context.update(
                {
                    "chunk": chunk_key,
                    "tiles": tiles,
                    "chunk_size": chunk_size,
                    "tile_size": tile_size,
                }
            )
            self._dispatch_event(norm_event, chunk_context)

    def _dispatch_event(self, event_name: str, context: Dict[str, Any]) -> None:
        rules = self._config_loader.rules_for_event(event_name)
        if not rules:
            return
        for rule in rules:
            if rule.requires_exact_position:
                self._process_exact_position_rule(rule, context)
            else:
                self._process_generated_rule(rule, context)

    def _process_exact_position_rule(
        self,
        rule: SpawnRule,
        context: Dict[str, Any],
    ) -> None:
        world_position = context.get("world_position")
        if world_position is None:
            return
        self._spawn_entity(rule.entity_id, tuple(world_position))

    def _process_generated_rule(
        self,
        rule: SpawnRule,
        context: Dict[str, Any],
    ) -> None:
        tiles = context.get("tiles")
        chunk = context.get("chunk")
        if tiles is None or chunk is None:
            return
        chunk_size = int(context.get("chunk_size") or tiles.shape[0] or self._chunk_size)
        tile_size = int(context.get("tile_size") or self._tile_size)

        player_tile = self._player_tile_coord(tile_size)

        if rule.spawn_per == "island":
            self._spawn_per_island(rule, chunk, tiles, chunk_size, tile_size, player_tile)
        elif rule.spawn_per == "void":
            self._spawn_per_void(rule, chunk, tiles, chunk_size, tile_size, player_tile)
        elif rule.spawn_per == "tile":
            self._spawn_per_tile(rule, chunk, tiles, chunk_size, tile_size, player_tile)
        elif rule.spawn_per == "event":
            # Event-driven rule but no explicit world position provided.
            return
        else:
            raise ValueError(f"Unsupported spawn_per '{rule.spawn_per}' for {rule.entity_id}")

    # --- Spawn strategies ----------------------------------------------
    def _spawn_per_tile(
        self,
        rule: SpawnRule,
        chunk_key: ChunkKey,
        tiles: np.ndarray,
        chunk_size: int,
        tile_size: int,
        player_tile: Optional[TileCoord],
    ) -> None:
        coords = eligible_coordinates(tiles, rule.eligible_tiles)
        coords = filter_by_player_range(
            coords, chunk_key, chunk_size, player_tile, rule.player_range_tiles
        )
        if not coords:
            return
        for coord in coords:
            if self._rng.random() > rule.spawn_chance:
                continue
            count = max(0, rule.roll_count(self._rng))
            if count <= 0:
                continue
            placements: List[TileCoord]
            if rule.allow_shared_tile:
                placements = [coord] * count
            else:
                placements = [coord]
            self._spawn_at_tiles(rule.entity_id, placements, chunk_key, chunk_size, tile_size)

    def _spawn_per_island(
        self,
        rule: SpawnRule,
        chunk_key: ChunkKey,
        tiles: np.ndarray,
        chunk_size: int,
        tile_size: int,
        player_tile: Optional[TileCoord],
    ) -> None:
        land_mask = tiles != TILE_CODE_VOID
        islands = find_regions(land_mask)
        for island in islands:
            island_coords = [
                coord
                for coord in island
                if tile_is_eligible(tiles, coord, rule.eligible_tiles)
            ]
            island_coords = filter_by_player_range(
                island_coords, chunk_key, chunk_size, player_tile, rule.player_range_tiles
            )
            if not island_coords:
                continue
            if self._rng.random() > rule.spawn_chance:
                continue
            spawn_count = max(0, rule.roll_count(self._rng))
            if spawn_count <= 0:
                continue
            positions = choose_positions(
                island_coords, spawn_count, rule.allow_shared_tile, self._rng
            )
            self._spawn_at_tiles(rule.entity_id, positions, chunk_key, chunk_size, tile_size)

    def _spawn_per_void(
        self,
        rule: SpawnRule,
        chunk_key: ChunkKey,
        tiles: np.ndarray,
        chunk_size: int,
        tile_size: int,
        player_tile: Optional[TileCoord],
    ) -> None:
        void_mask = tiles == TILE_CODE_VOID
        void_regions = find_regions(void_mask)
        for region in void_regions:
            coords = [
                coord
                for coord in region
                if tile_is_eligible(
                    tiles, coord, rule.eligible_tiles, include_void=True
                )
            ]
            coords = filter_by_player_range(
                coords, chunk_key, chunk_size, player_tile, rule.player_range_tiles
            )
            if not coords:
                continue
            if self._rng.random() > rule.spawn_chance:
                continue
            spawn_count = max(0, rule.roll_count(self._rng))
            if spawn_count <= 0:
                continue
            positions = choose_positions(
                coords, spawn_count, rule.allow_shared_tile, self._rng
            )
            self._spawn_at_tiles(rule.entity_id, positions, chunk_key, chunk_size, tile_size)

    # --- Helpers -------------------------------------------------------
    def _spawn_at_tiles(
        self,
        entity_id: str,
        coords: Sequence[TileCoord],
        chunk_key: ChunkKey,
        chunk_size: int,
        tile_size: int,
    ) -> None:
        if not coords:
            return
        for coord in coords:
            world_position = self._tile_to_world(chunk_key, coord, chunk_size, tile_size)
            self._spawn_entity(entity_id, world_position)

    def _spawn_entity(self, entity_id: str, position: Tuple[float, float]) -> Entity:
        if not self._world or not self._entity_manager:
            raise RuntimeError("MonsterFactoryService requires world/entity_manager binding")
        entity = evolvable_registry.spawn(entity_id, self._world, self._entity_manager)
        position_comp = self._world.get(entity, Position)
        if position_comp:
            position_comp.x = float(position[0])
            position_comp.y = float(position[1])
        else:
            self._world.add(
                entity,
                Position(x=float(position[0]), y=float(position[1])),
            )
        return entity

    def _choose_positions(
        self,
        available: Sequence[TileCoord],
        count: int,
        allow_shared: bool,
    ) -> List[TileCoord]:
        if not available or count <= 0:
            return []
        if allow_shared:
            return [available[self._rng.randrange(len(available))] for _ in range(count)]
        unique = list(available)
        self._rng.shuffle(unique)
        return list(unique[: min(count, len(unique))])

    def _tile_to_world(
        self,
        chunk_key: ChunkKey,
        coord: TileCoord,
        chunk_size: int,
        tile_size: int,
    ) -> Tuple[float, float]:
        chunk_world_x = chunk_key[0] * chunk_size * tile_size
        chunk_world_y = chunk_key[1] * chunk_size * tile_size
        world_x = chunk_world_x + coord[0] * tile_size + tile_size * 0.5
        world_y = chunk_world_y + coord[1] * tile_size + tile_size * 0.5
        return (float(world_x), float(world_y))

    def _player_tile_coord(self, tile_size: int) -> Optional[TileCoord]:
        if not self._world:
            return None
        for entity, _player in self._world.view(Player):
            pos = self._world.get(entity, Position)
            if pos is None:
                continue
            tile_x = int(pos.x // tile_size)
            tile_y = int(pos.y // tile_size)
            return (tile_x, tile_y)
        return None

    def _normalize_event_name(self, name: str) -> str:
        return str(name or "").strip().lower()

    def _ensure_entity_factories_loaded(self) -> None:
        modules = [
            "ecs_core.entities.flora.sprout",
            "ecs_core.entities.flora.twice_sprout",
            "ecs_core.entities.flora.thrice_sprout",
            "ecs_core.entities.flora.quarce_sprout",
            "ecs_core.entities.skeleton",
        ]
        for module in modules:
            try:
                importlib.import_module(module)
            except ImportError:
                raise

__all__ = ["MonsterFactoryService"]
