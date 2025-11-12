import random
import pygame
from typing import Tuple
from components.components import Drops, Health, Position


class DropsSystem:
    def __init__(self):
        self.world = None
        self.inventory_service = None  # For coin spawning

    def update(self, dt: float):
        for eid, (health, drops) in list(self.world.get_components(Health, Drops)):
            if health.current_health <= 0 and eid in self.world.components:  # Just died
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
            xp_event = pygame.event.Event(pygame.USEREVENT + 1, {"type": "ADD_XP", "amount": drops.xp})
            pygame.event.post(xp_event)

    def _spawn_coin(self, coin_name: str, pos: Tuple[int, int]):
        # Create pickup entity from inventory data
        pickup_eid = self.inventory_service.create_pickup(coin_name, pos)
        # Assumes inventory_service spawns entity with Pickup component
