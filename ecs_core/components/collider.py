from dataclasses import dataclass
import constants


@dataclass
class Collider:
    diameter: int
    offset_x: int = 0
    offset_y: int = 0
    layer: int = constants.LAYER_ENEMY
    mask: int = constants.LAYER_ENEMY
    is_trigger: bool = False
    enabled: bool = True
    immovable: bool = False
