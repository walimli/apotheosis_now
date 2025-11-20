"""Geometry helpers specific to fence placement."""

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

Vec2f = Tuple[float, float]
Point2f = Tuple[float, float]
Polygon = Sequence[Point2f]
AABB = Tuple[float, float, float, float]

_HALF_TILE = 32.0


def transform_local64_to_world(
    points: Sequence[Point2f],
    center: Vec2f,
    scale: float,
    offsets: Tuple[float, float],
) -> Tuple[Point2f, ...]:
    """Transform local 64x64 points into world space around a centre point."""
    cx, cy = center
    ox, oy = offsets
    sx = float(scale)
    sy = float(scale)
    transformed: list[Point2f] = []
    for px, py in points:
        wx = cx + ((float(px) - _HALF_TILE + float(ox)) * sx)
        wy = cy + ((float(py) - _HALF_TILE + float(oy)) * sy)
        transformed.append((wx, wy))
    return tuple(transformed)


def aabb_from_points(points: Iterable[Point2f]) -> AABB:
    """Compute an axis-aligned bounding box for a set of points."""
    xs = []
    ys = []
    for x, y in points:
        xs.append(float(x))
        ys.append(float(y))
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def aabb_overlap(a: AABB, b: AABB) -> bool:
    """Return True when two AABBs overlap."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return (ax0 < bx1) and (ax1 > bx0) and (ay0 < by1) and (ay1 > by0)
