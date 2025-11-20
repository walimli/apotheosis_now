import random
import pygame
from typing import Tuple
from ecs_core.components import Drops, Health, Position
from ecs_core.entities.inventory_entities import spawn_coin_at_position


class DropsSystem:
    def __init__(self):
        self.world = None
        self.entity_manager = None
        self.monster_factory = None

    def update(self, dt: float):
        for eid, (health, drops) in list(self.world.get_components(Health, Drops)):
            if (
                health.current_health <= 0
                and self.world
                and self.world.has_entity(eid)
            ):
                self._handle_death(eid, drops)
                self.world.destroy_entity(eid)  # Cleanup

    def _handle_death(self, eid: int, drops: Drops):
        pos = self.world.get_component(eid, Position)
        drop_pos = (pos.x, pos.y) if pos else (0, 0)

        # Coins: deterministic + probabilistic
        for coin_name, drop_rate in drops.coins.items():
            # Guaranteed floor drops
            guaranteed = int(drop_rate)
            for _ in range(guaranteed):
                self._spawn_coin(coin_name, drop_pos)

            # Fractional chance
            chance = drop_rate % 1.0
            if chance > 0 and random.random() < chance:
                self._spawn_coin(coin_name, drop_pos)

        # XP event - use pygame custom event system
        if drops.xp > 0:
            xp_event = pygame.event.Event(
                pygame.USEREVENT + 1,
                {"amount": drops.xp},
            )
            pygame.event.post(xp_event)

    def _spawn_coin(self, coin_name: str, pos: Tuple[int, int]):
        # Spawn coin entity with bounce behavior
        if self.monster_factory:
            self.monster_factory.spawn_attack_entity(coin_name, pos)
        elif self.world and self.entity_manager:
            # Fallback if factory not bound (though it should be)
            spawn_coin_at_position(
                self.world,
                self.entity_manager,
                pos,
                coin_value=1,
                registry_id=coin_name,
                inventory_item_id=coin_name,
            )
