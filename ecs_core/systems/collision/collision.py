from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import math
from ecs_core.components.collider import Collider

LAYER_PLAYER = 1 << 0
LAYER_ENEMY = 1 << 1
LAYER_PROJECTILE = 1 << 2
LAYER_WALL = 1 << 3
LAYER_PICKUP = 1 << 4


@dataclass
class CollisionEvent:
    a: int
    b: int
    normal: Tuple[float, float]
    penetration: float


@dataclass
class HitInfo:
    entity_id: int
    point: Tuple[float, float]
    normal: Tuple[float, float]
    distance: float


class CollisionSystem:
    def __init__(self, *, cell_size: int = 128):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[int]] = {}
        self.colliders: Dict[int, Collider] = {}
        self.entity_pos: Dict[int, Tuple[int, int]] = {}
        self.events: List[CollisionEvent] = []

    def register(self, entity_id: int, collider: Collider, pos: Tuple[int, int]):
        self.colliders[entity_id] = collider
        self.entity_pos[entity_id] = pos

    def unregister(self, entity_id: int):
        if entity_id in self.colliders:
            del self.colliders[entity_id]
            del self.entity_pos[entity_id]

    def update_positions(self, positions: Dict[int, Tuple[int, int]]):
        self.entity_pos.update(positions)
        self._rebuild_grid()

    def update(self) -> List[CollisionEvent]:
        self.events.clear()
        self._rebuild_grid()
        self._process_collisions()
        return self.events

    def _rebuild_grid(self):
        self.grid.clear()
        for entity_id, pos in self.entity_pos.items():
            collider = self.colliders.get(entity_id)
            if collider is None or not collider.enabled:
                continue
            center = (
                pos[0] + collider.offset_x,
                pos[1] + collider.offset_y,
            )
            radius = collider.diameter // 2
            min_x, max_x = center[0] - radius, center[0] + radius
            min_y, max_y = center[1] - radius, center[1] + radius

            start_cell_x = min_x // self.cell_size
            end_cell_x = (max_x // self.cell_size) + 1
            start_cell_y = min_y // self.cell_size
            end_cell_y = (max_y // self.cell_size) + 1

            for cell_x in range(start_cell_x, end_cell_x):
                for cell_y in range(start_cell_y, end_cell_y):
                    cell_hash = (cell_x, cell_y)
                    bucket = self.grid.setdefault(cell_hash, [])
                    bucket.append(entity_id)

    def _process_collisions(self):
        processed = set()
        for cell_hash, entities in self.grid.items():
            for i, id_a in enumerate(entities):
                for id_b in entities[i + 1 :]:
                    if (id_a, id_b) in processed or (id_b, id_a) in processed:
                        continue
                    processed.add((id_a, id_b))

                    coll_a = self.colliders[id_a]
                    coll_b = self.colliders[id_b]

                    if not (coll_a.mask & coll_b.layer) or not (
                        coll_b.mask & coll_a.layer
                    ):
                        continue

                    pos_a = self.entity_pos[id_a]
                    pos_b = self.entity_pos[id_b]
                    center_a = (pos_a[0] + coll_a.offset_x, pos_a[1] + coll_a.offset_y)
                    center_b = (pos_b[0] + coll_b.offset_x, pos_b[1] + coll_b.offset_y)
                    r_a = coll_a.diameter // 2
                    r_b = coll_b.diameter // 2

                    if self._circle_collide(center_a, r_a, center_b, r_b):
                        info = self._build_collision_info(
                            id_a, id_b, center_a, r_a, center_b, r_b
                        )
                        self.events.append(info)

                        if not (coll_a.is_trigger or coll_b.is_trigger):
                            self._resolve_overlap(id_a, id_b, info)

    def _circle_collide(
        self, c1: Tuple[int, int], r1: int, c2: Tuple[int, int], r2: int
    ) -> bool:
        dx = c1[0] - c2[0]
        dy = c1[1] - c2[1]
        return dx * dx + dy * dy < (r1 + r2) * (r1 + r2)

    def _build_collision_info(
        self,
        id_a: int,
        id_b: int,
        c1: Tuple[int, int],
        r1: int,
        c2: Tuple[int, int],
        r2: int,
    ) -> CollisionEvent:
        dx = c2[0] - c1[0]
        dy = c2[1] - c1[1]
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq)
        if dist == 0:
            normal = (1.0, 0.0)
        else:
            normal = (dx / dist, dy / dist)
        penetration = r1 + r2 - dist
        return CollisionEvent(
            id_a if id_a < id_b else id_b,
            id_b if id_a < id_b else id_a,
            normal,
            penetration,
        )

    def _resolve_overlap(self, id_a: int, id_b: int, info: CollisionEvent):
        correction = (
            info.normal[0] * info.penetration * 0.5,
            info.normal[1] * info.penetration * 0.5,
        )
        pos_a = list(self.entity_pos[id_a])
        pos_b = list(self.entity_pos[id_b])
        pos_a[0] -= correction[0]
        pos_a[1] -= correction[1]
        pos_b[0] += correction[0]
        pos_b[1] += correction[1]
        self.entity_pos[id_a] = tuple(pos_a)
        self.entity_pos[id_b] = tuple(pos_b)

    def query_circle(
        self, center: Tuple[int, int], radius: int, layer_mask: int = -1
    ) -> List[int]:
        results = set()
        min_x = center[0] - radius
        max_x = center[0] + radius
        min_y = center[1] - radius
        max_y = center[1] + radius

        start_cell_x = min_x // self.cell_size
        end_cell_x = (max_x // self.cell_size) + 1
        start_cell_y = min_y // self.cell_size
        end_cell_y = (max_y // self.cell_size) + 1

        for cell_x in range(start_cell_x, end_cell_x):
            for cell_y in range(start_cell_y, end_cell_y):
                cell_hash = (cell_x, cell_y)
                bucket = self.grid.get(cell_hash)
                if bucket:
                    for entity_id in bucket:
                        coll = self.colliders[entity_id]
                        if not coll.enabled or (
                            layer_mask != -1 and not (coll.layer & layer_mask)
                        ):
                            continue
                        entity_center = (
                            self.entity_pos[entity_id][0] + coll.offset_x,
                            self.entity_pos[entity_id][1] + coll.offset_y,
                        )
                        if self._circle_collide(
                            center, radius, entity_center, coll.diameter // 2
                        ):
                            results.add(entity_id)
        return list(results)

    def raycast(
        self, start: Tuple[float, float], end: Tuple[float, float], layer_mask: int = -1
    ) -> Optional[HitInfo]:
        dir_x = end[0] - start[0]
        dir_y = end[1] - start[1]
        length = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if length == 0:
            return None
        dir_x /= length
        dir_y /= length

        min_t = float("inf")
        closest_id = None
        closest_point = None
        closest_normal = None

        steps = max(1, int(length))
        for i in range(steps):
            t = i / steps
            current = (start[0] + dir_x * length * t, start[1] + dir_y * length * t)

            candidates = self.query_circle(current, 1, layer_mask)
            for entity_id in candidates:
                coll = self.colliders[entity_id]
                entity_center = (
                    self.entity_pos[entity_id][0] + coll.offset_x,
                    self.entity_pos[entity_id][1] + coll.offset_y,
                )
                r = coll.diameter // 2

                dx = entity_center[0] - current[0]
                dy = entity_center[1] - current[1]
                dist_to_center = math.sqrt(dx * dx + dy * dy)

                if dist_to_center <= r:
                    proj_t = (dx * dir_x + dy * dir_y) / (r * 2)
                    hit_t = t - (r - dist_to_center) / length
                    if 0 <= hit_t <= 1 and hit_t < min_t:
                        min_t = hit_t
                        closest_id = entity_id
                        closest_point = (current[0] + dx * 0.5, current[1] + dy * 0.5)
                        closest_normal = (-dir_x, -dir_y)

        if closest_id is not None:
            return HitInfo(closest_id, closest_point, closest_normal, min_t * length)
        return None
