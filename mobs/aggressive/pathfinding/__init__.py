"""Aggressive mob pathfinding utilities.

Phase 1 introduces grid helpers that translate world-space coordinates into
tile coordinates, verify walkability, and enumerate temporary blockers.
Phase 2 layers on an A* planner with caching suitable for aggressive mobs.
"""

from ....ecs_core.systems.pathfinding.combat import (
    AttackApproach,
    plan_attack_approach,
    should_force_replan,
)
from ....ecs_core.systems.pathfinding.grid import (
    AggressiveGridContext,
    collect_blocking_tiles,
)
from ....ecs_core.systems.pathfinding.navigation import (
    AggressiveNavigator,
    NavigationPlan,
)
from ....ecs_core.systems.pathfinding.planner import AggressivePathfinder, PathResult

__all__ = [
    "AttackApproach",
    "AggressiveGridContext",
    "AggressiveNavigator",
    "AggressivePathfinder",
    "NavigationPlan",
    "PathResult",
    "collect_blocking_tiles",
    "plan_attack_approach",
    "should_force_replan",
]
