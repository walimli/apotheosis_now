from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple, TYPE_CHECKING

import pygame

from systems.audio_package import publish_audio_event
from systems.mobs.core import behavior
from systems.mobs.core.behavior_dispatch import (
    MobBehaviorType,
    resolve_factory_for_species,
)

from constants import CHUNK_PIXELS
from states.play_state.render_types import RenderPacket
from systems.asset_loader.mob_assets import MobAssetProvider
from systems.mobs.core.base_view import BaseMobView
from systems.mobs.core.species_loader import MobSpec

if TYPE_CHECKING:
    from systems.drops.manager import DropManager
from systems.void import VoidConfig, VoidManager


@dataclass
class MobInstance:
    spec: MobSpec
    model: Any
    controller: Any
    view: BaseMobView
    void_tracker: Optional["MobVoidTracker"] = None
    drop_spawned: bool = False


class MobVoidTracker:
    """Adapter that applies VoidManager damage ticks to a mob model."""

    def __init__(self, model: Any, controller: Any, view: BaseMobView, config: VoidConfig) -> None:
        self._model = model
        self._controller = controller
        self._view = view
        self._world = None
        self._void_manager = VoidManager(
            tile_lookup=self._tile_lookup,
            damage_callback=self._apply_damage,
            config=VoidConfig(
                damage_amount=config.damage_amount,
                damage_interval=config.damage_interval,
                void_tiles=tuple(config.void_tiles),
            ),
        )

    def set_world(self, world) -> None:
        self._world = world

    def set_enabled(self, enabled: bool) -> None:
        self._void_manager.set_enabled(enabled)

    def update(self, dt: float) -> None:
        if self._world is None:
            return
        if getattr(self._model, "is_dead", False):
            self._void_manager.set_enabled(False)
            return
        width, height = self._view.footprint_px
        world_x = float(getattr(self._model, "x", 0.0)) + width * 0.5
        world_y = float(getattr(self._model, "y", 0.0)) + height * 0.5
        self._void_manager.update(dt, world_x, world_y)

    def _tile_lookup(self, world_x: float, world_y: float) -> Optional[int]:
        world = self._world
        if world is None:
            return None
        return behavior.get_tile_id_at_world(world, world_x, world_y)

    def _apply_damage(self, amount: int) -> None:
        if amount <= 0:
            return
        if getattr(self._model, "is_dead", False):
            return
        hp_cur = getattr(self._model, "hp_cur", None)
        if hp_cur is None:
            return
        new_hp = max(0, int(hp_cur) - int(amount))
        self._model.hp_cur = new_hp
        if new_hp <= 0:
            self._model.hp_cur = 0
            handler = getattr(self._controller, "register_hit", None)
            if callable(handler):
                handler(lethal=True)
            else:
                setattr(self._model, "is_dead", True)


class MobManager:
    """Minimal runtime holder for mob instances."""

    def __init__(
        self,
        assets: MobAssetProvider,
        species: Dict[str, MobSpec],
        factories: Mapping[str, Any] | None = None,
    ) -> None:
        self.assets = assets
        self.species = species
        factory_map = dict(factories or {})
        self._behavior_factories: Dict[MobBehaviorType, Any] = {}
        self._fallback_factories: Dict[str, Any] = {}
        for key, value in factory_map.items():
            if isinstance(key, MobBehaviorType):
                self._behavior_factories[key] = value
            else:
                self._fallback_factories[str(key)] = value
        self._instances: List[MobInstance] = []
        self._next_id = 1
        self._void_config: Optional[VoidConfig] = None
        self._drop_manager: Optional["DropManager"] = None
        self._targeting_on_added: Optional[Callable[[MobInstance], None]] = None
        self._targeting_on_removed: Optional[Callable[[MobInstance], None]] = None
        self._targeting_on_moved: Optional[Callable[[MobInstance], None]] = None
        self._targeting_recompute: Optional[Callable[[], None]] = None
        self._targeting_last_rects: Dict[int, Tuple[int, int, int, int]] = {}

    # --- Public API ---
    def spawn(self, species_id: str, pos_px: Tuple[float, float]) -> None:
        spec = self.species[species_id]
        instance = self._create_instance(spec, pos_px)
        self._instances.append(instance)
        publish_audio_event("mob.spawn")
        self._next_id += 1
        self._emit_targeting_added(instance)

    def set_void_damage_config(self, config: VoidConfig) -> None:
        if not isinstance(config, VoidConfig):
            raise TypeError("MobManager.set_void_damage_config expects VoidConfig")
        self._void_config = VoidConfig(
            damage_amount=config.damage_amount,
            damage_interval=config.damage_interval,
            void_tiles=tuple(config.void_tiles),
        )

    def set_drop_manager(self, manager: "DropManager") -> None:
        self._drop_manager = manager

    def set_targeting_hooks(
        self,
        *,
        on_added: Optional[Callable[[MobInstance], None]] = None,
        on_removed: Optional[Callable[[MobInstance], None]] = None,
        on_moved: Optional[Callable[[MobInstance], None]] = None,
        recompute: Optional[Callable[[], None]] = None,
    ) -> None:
        self._targeting_on_added = on_added
        self._targeting_on_removed = on_removed
        self._targeting_on_moved = on_moved
        self._targeting_recompute = recompute
        self._targeting_last_rects = {}
        for instance in self._instances:
            key = self._targeting_entity_key(instance)
            rect = self._mob_rect_tuple(instance)
            if key is not None and rect is not None:
                self._targeting_last_rects[key] = rect

    def update(self, dt: float, player, time_manager, world) -> None:
        del time_manager  # world updates only need player/world for controllers

        survivors: List[MobInstance] = []
        for instance in self._instances:
            instance.controller.update(dt, player, world)
            instance.view.update(dt)
            self._update_void_tracker(instance, world, dt)
            self._handle_drop_spawn(instance)
            self._track_targeting_motion(instance)
            if self._should_remove(instance):
                self._emit_targeting_removed(instance)
                continue
            survivors.append(instance)
        self._instances = survivors

    def draw(self, surface: pygame.Surface, camera=None) -> None:
        packets = sorted(
            self.render_packets(camera), key=lambda p: (p.baseline, p.z, p.order)
        )
        for packet in packets:
            surface.blit(packet.surface, packet.position)

    def render_packets(self, camera=None) -> List[RenderPacket]:
        packets: List[RenderPacket] = []
        for instance in self._instances:
            packet = instance.view.render_packet(camera)
            if packet is not None:
                packets.append(packet)
        return packets

    def iter_instances(self) -> Iterable[MobInstance]:
        """Return an iterable snapshot of active mob instances."""
        return tuple(self._instances)

    # --- Persistence ---
    def to_dict(self) -> list:
        out = []
        for instance in self._instances:
            model = instance.model
            out.append(
                {
                    "s": str(getattr(model, "species_id", "")),
                    "x": float(getattr(model, "x", 0.0)),
                    "y": float(getattr(model, "y", 0.0)),
                    "f": str(getattr(model, "facing", "down")),
                    "hp": int(getattr(model, "hp_cur", 0)),
                    "cd": float(getattr(model, "cooldown_left", 0.0)),
                }
            )
        return out

    def from_dict(self, data: list) -> None:
        if not isinstance(data, list):
            raise TypeError("MobManager.from_dict: expected list")
        self._instances.clear()
        self._next_id = 1
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("MobManager.from_dict: entry must be dict")
            sid = str(entry.get("s"))
            if sid not in self.species:
                raise ValueError(f"MobManager.from_dict: unknown species '{sid}'")
            spec = self.species[sid]
            instance = self._create_instance(
                spec, (float(entry.get("x")), float(entry.get("y")))
            )
            model = instance.model
            model.facing = str(entry.get("f", "down"))
            model.hp_cur = max(0, min(int(model.hp_max), int(entry.get("hp"))))
            model.cooldown_left = max(0.0, float(entry.get("cd", 0.0)))
            self._instances.append(instance)
            self._next_id += 1

    # --- Internals ---
    def _create_instance(self, spec: MobSpec, pos_px: Tuple[float, float]) -> MobInstance:
        factory = resolve_factory_for_species(
            spec.id,
            self._behavior_factories,
            fallback_factories=self._fallback_factories,
        )
        model, controller, view = factory(self._next_id, spec, pos_px, self.assets)
        if not isinstance(view, BaseMobView):
            raise TypeError("Mob factory must return (model, controller, BaseMobView)")
        return MobInstance(spec=spec, model=model, controller=controller, view=view)

    def _should_remove(self, instance: MobInstance) -> bool:
        predicate = getattr(instance.controller, "should_despawn", None)
        if predicate is None:
            raise AttributeError(
                f"Controller for '{instance.spec.id}' is missing should_despawn()"
            )
        return bool(predicate())

    def _targeting_entity_key(self, instance: MobInstance) -> Optional[int]:
        model = getattr(instance, "model", None)
        if model is None:
            return None
        entity_id = getattr(model, "id", None)
        if entity_id is None:
            return None
        return int(entity_id)

    def _mob_rect_tuple(self, instance: MobInstance) -> Optional[Tuple[int, int, int, int]]:
        model = getattr(instance, "model", None)
        view = getattr(instance, "view", None)
        if model is None or view is None:
            return None
        width, height = getattr(view, "footprint_px", (0, 0))
        x = int(float(getattr(model, "x", 0.0)))
        y = int(float(getattr(model, "y", 0.0)))
        return (x, y, int(width), int(height))

    def _emit_targeting_added(self, instance: MobInstance) -> None:
        if self._targeting_on_added is None:
            return
        self._targeting_on_added(instance)
        self._track_rect_snapshot(instance)
        if self._targeting_recompute is not None:
            self._targeting_recompute()

    def _emit_targeting_removed(self, instance: MobInstance) -> None:
        key = self._targeting_entity_key(instance)
        if key is not None:
            self._targeting_last_rects.pop(key, None)
        if self._targeting_on_removed is None:
            return
        self._targeting_on_removed(instance)
        if self._targeting_recompute is not None:
            self._targeting_recompute()

    def _track_targeting_motion(self, instance: MobInstance) -> None:
        self._track_rect_snapshot(instance, emit=True)

    def _track_rect_snapshot(self, instance: MobInstance, emit: bool = False) -> None:
        key = self._targeting_entity_key(instance)
        if key is None:
            return
        rect = self._mob_rect_tuple(instance)
        if rect is None:
            return
        last = self._targeting_last_rects.get(key)
        if last == rect:
            return
        self._targeting_last_rects[key] = rect
        if emit and self._targeting_on_moved is not None:
            self._targeting_on_moved(instance)
            if self._targeting_recompute is not None:
                self._targeting_recompute()






    def count_alive(self, species_id: str, chunk: Optional[Tuple[int, int]] = None) -> int:
        count = 0
        for instance in self._instances:
            model = instance.model
            if getattr(model, "species_id", None) != species_id:
                continue
            if getattr(model, "is_dead", False):
                continue
            if chunk is not None:
                model_chunk = (
                    int(getattr(model, "x", 0.0) // CHUNK_PIXELS),
                    int(getattr(model, "y", 0.0) // CHUNK_PIXELS),
                )
                if model_chunk != chunk:
                    continue
            if self._should_remove(instance):
                continue
            count += 1
        return count

    def _update_void_tracker(self, instance: MobInstance, world, dt: float) -> None:
        if self._void_config is None:
            return
        if instance.void_tracker is None:
            instance.void_tracker = MobVoidTracker(
                instance.model,
                instance.controller,
                instance.view,
                self._void_config,
            )
        tracker = instance.void_tracker
        tracker.set_world(world)
        tracker.update(dt)

    def _handle_drop_spawn(self, instance: MobInstance) -> None:
        if instance.drop_spawned:
            return
        model = instance.model
        if not getattr(model, "is_dead", False):
            return
        instance.drop_spawned = True
        if self._drop_manager is None:
            return
        drops = getattr(instance.spec, "drops", ())
        if not drops:
            return
        foot_w, foot_h = instance.view.footprint_px
        world_x = float(getattr(model, "x", 0.0)) + float(foot_w) * 0.5
        world_y = float(getattr(model, "y", 0.0)) + float(foot_h) * 0.5
        self._drop_manager.spawn_from_table(drops, (world_x, world_y))






