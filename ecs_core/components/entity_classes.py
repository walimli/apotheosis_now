# components/entity_classes.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    """Player entity marker component
    
    Used to identify player-controlled entities in the ECS system.
    Players can receive input and are typically the main game entities.
    """
    pass


@dataclass(frozen=True)
class Mob:
    """Mobile NPC/enemy marker component
    
    Used to identify mobile non-player characters, enemies, and creatures
    that have AI and can move around the game world.
    """
    pass


@dataclass(frozen=True)
class NPC:
    """Static NPC marker component
    
    Used to identify non-player characters that are stationary
    and typically provide dialogue, services, or quests.
    """
    pass


@dataclass(frozen=True)
class Plant:
    """Plant/vegetation marker component
    
    Used to identify plant entities that can grow, be harvested,
    and interact with the environment (trees, crops, flowers, etc.).
    """
    pass


@dataclass(frozen=True)
class Object:
    """Static environmental object marker component
    
    Used to identify static environmental objects that don't move
    but can be interacted with (rocks, buildings, tools, etc.).
    """
    pass