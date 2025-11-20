from ecs_core.components import Health, Position


class HealthSystem:
    def __init__(self):
        self.world = None
        self.time_service = None  # Set externally for HEARTBEAT

    def take_damage(self, entity_id: int, damage: int) -> bool:
        """Returns True if entity died."""
        health = self.world.get_component(entity_id, Health)
        if not health:
            return False

        reduced_damage = max(0, damage - health.defense)
        health.current_health = max(0, health.current_health - reduced_damage)

        if health.sound:
            self.audio_service.play(health.sound)  # Set audio_service externally

        return health.current_health <= 0

    def is_dead(self, entity_id: int) -> bool:
        health = self.world.get_component(entity_id, Health)
        return health and health.current_health <= 0

    def heal(self, entity_id: int, amount: int):
        health = self.world.get_component(entity_id, Health)
        if health:
            health.current_health = min(
                health.max_health, health.current_health + amount
            )

    def update(self, dt: float):
        # Regen on HEARTBEAT (call when current_event == "HEARTBEAT")
        if (
            self.time_service
            and self.time_service.current_event == "HEARTBEAT"
        ):
            for eid, health in self.world.get_component(Health):
                if health.regeneration > 0 and not self.is_dead(eid):
                    self.heal(eid, health.regeneration)
