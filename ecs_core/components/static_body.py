from dataclasses import dataclass


@dataclass(frozen=True)
class StaticBody:
    """Marks an entity as immovable for collision resolution."""


__all__ = ["StaticBody"]
