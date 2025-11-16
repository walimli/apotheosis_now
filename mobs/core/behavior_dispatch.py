from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class MobBehaviorType(str, Enum):
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    NPC = "npc"
    BOSS = "boss"


_SPECIES_BEHAVIOR: Dict[str, MobBehaviorType] = {
    "skeleton_basic": MobBehaviorType.AGGRESSIVE,
    "wisp": MobBehaviorType.NPC,
}


def get_behavior_type(species_id: str) -> MobBehaviorType:
    try:
        return _SPECIES_BEHAVIOR[species_id]
    except KeyError as exc:
        raise KeyError(f"No behavior type registered for species '{species_id}'") from exc


def register_behavior_type(species_id: str, behavior_type: MobBehaviorType) -> None:
    if not species_id:
        raise ValueError("species_id must be a non-empty string")
    _SPECIES_BEHAVIOR[species_id] = behavior_type


def resolve_factory_for_species(
    species_id: str,
    behavior_factories: Dict[MobBehaviorType, Any],
    *,
    fallback_factories: Dict[str, Any] | None = None,
) -> Any:
    behavior_type = get_behavior_type(species_id)
    factory = behavior_factories.get(behavior_type)
    if factory is not None:
        return factory

    if fallback_factories is not None:
        by_id = fallback_factories.get(species_id)
        if by_id is not None:
            return by_id

    raise KeyError(
        f"No factory registered for behavior '{behavior_type.value}' (species '{species_id}')"
    )
