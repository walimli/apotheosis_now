from __future__ import annotations

from typing import Callable, Dict, Optional


class Progression:
    """Player progression tuned for roguelite runs.

    Tracks raw experience, emerald currency, and per-upgrade levels.
    No implicit fallbacks or auto-granting: state transitions must be explicit.
    """

    XP_PER_EMERALD = 100

    BASE_DAMAGE = 1
    BASE_MAX_HEALTH = 10
    BASE_SPEED_PX_S = 256.0
    BASE_SOUL = 100

    MIGHT_PER_LEVEL = 1
    HEALTH_PER_LEVEL = 2
    SPEED_PER_LEVEL = 16.0
    SOUL_PER_LEVEL = 25
    BASE_FORTUNE_CHANCE = 0.01  # 1% base spawn chance even at level 0
    FORTUNE_CHANCE_PER_LEVEL = 0.01  # +1% spawn chance per fortune level

    UPGRADE_KEYS = ("might", "health", "speed", "fortune", "octopus", "formula")

    def __init__(self) -> None:
        self.xp: int = 0
        self.emeralds: int = 0
        self._upgrades: Dict[str, int] = {key: 0 for key in self.UPGRADE_KEYS}
        self._on_stats_changed: Optional[Callable[[], None]] = None
        self._on_formula_leveled: Optional[Callable[[int], None]] = None

    # --- XP / Emerald handling ---
    def add_xp(self, amount: int) -> None:
        if amount <= 0:
            return
        self.xp += int(amount)
        minted = self.xp // self.XP_PER_EMERALD
        if minted > 0:
            self.emeralds += minted
            # Leave remainder XP; do not reset to zero
            self.xp = self.xp % self.XP_PER_EMERALD

    def convert_xp_to_emeralds(self) -> int:
        minted = self.xp // self.XP_PER_EMERALD
        if minted <= 0:
            return 0
        self.emeralds += minted
        # Remove only the converted amount; keep remainder XP
        self.xp -= minted * self.XP_PER_EMERALD
        return minted

    # --- Upgrades ---
    def get_upgrade_level(self, key: str) -> int:
        key = self._validate_key(key)
        return self._upgrades[key]

    def get_upgrade_cost(self, key: str) -> int:
        key = self._validate_key(key)
        return self._upgrades[key] + 1

    def purchase_upgrade(self, key: str) -> None:
        key = self._validate_key(key)
        cost = self.get_upgrade_cost(key)
        if self.emeralds < cost:
            raise ValueError(
                f"Not enough emeralds for {key}: have {self.emeralds}, need {cost}"
            )
        self.emeralds -= cost
        self._upgrades[key] += 1
        if key in ("might", "health", "speed", "octopus"):
            self._emit_stats_changed()
        if key == "formula" and self._on_formula_leveled is not None:
            # Notify listeners with the new level after purchase
            self._on_formula_leveled(self._upgrades[key])

    def _validate_key(self, key: str) -> str:
        if key not in self.UPGRADE_KEYS:
            raise KeyError(f"Unknown upgrade key '{key}'")
        return key

    # --- Derived stats ---
    def get_damage(self) -> int:
        return self.BASE_DAMAGE + self.MIGHT_PER_LEVEL * self._upgrades["might"]

    def get_max_health(self) -> int:
        return self.BASE_MAX_HEALTH + self.HEALTH_PER_LEVEL * self._upgrades["health"]

    def get_speed_px_s(self) -> float:
        return float(
            self.BASE_SPEED_PX_S + self.SPEED_PER_LEVEL * self._upgrades["speed"]
        )

    def get_max_soul(self) -> int:
        """Maximum soul (energy) granted by the octopus track."""
        level = self._upgrades["octopus"]
        max_soul = self.BASE_SOUL + self.SOUL_PER_LEVEL * level
        return int(max(0, max_soul))

    def get_fortune_spawn_chance(self) -> float:
        """Spawn probability modifier for treasure coins."""
        level = self._upgrades["fortune"]
        chance = self.BASE_FORTUNE_CHANCE + self.FORTUNE_CHANCE_PER_LEVEL * level
        return max(0.0, chance)

    # --- Wiring ---
    def set_on_stats_changed(self, fn: Optional[Callable[[], None]]) -> None:
        self._on_stats_changed = fn

    def _emit_stats_changed(self) -> None:
        if self._on_stats_changed is None:
            return
        self._on_stats_changed()

    # --- Formulas wiring ---
    def set_on_formula_leveled(self, fn: Optional[Callable[[int], None]]) -> None:
        self._on_formula_leveled = fn

    # --- Persistence ---
    def to_dict(self) -> dict:
        return {
            "xp": int(self.xp),
            "emeralds": int(self.emeralds),
            "upgrades": {key: int(val) for key, val in self._upgrades.items()},
        }

    def load_from_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise TypeError("Progression.load_from_dict expects dict")
        if "xp" not in data or "emeralds" not in data or "upgrades" not in data:
            raise KeyError("Progression.load_from_dict missing required fields")

        xp = int(data["xp"])
        emeralds = int(data["emeralds"])
        upgrades_blob = data["upgrades"]
        if not isinstance(upgrades_blob, dict):
            raise TypeError("Progression.load_from_dict upgrades must be dict")

        new_levels: Dict[str, int] = {}
        for key in self.UPGRADE_KEYS:
            val = int(upgrades_blob.get(key, 0))
            if val < 0:
                raise ValueError(f"Upgrade level for {key} cannot be negative")
            new_levels[key] = val

        self.xp = max(0, xp)
        self.emeralds = max(0, emeralds)
        self._upgrades = new_levels
        self._emit_stats_changed()
