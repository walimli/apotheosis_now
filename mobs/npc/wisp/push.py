from __future__ import annotations

from typing import Optional, Tuple

import pygame


def compute_push_delta(
    player,
    *,
    last_player_center: Optional[Tuple[float, float]],
    wisp_x: float,
    wisp_y: float,
    collider_size: Tuple[float, float],
    collider_offset: Tuple[float, float],
    wisp_speed_px_s: float,
    dt: float,
) -> Tuple[Tuple[float, float], Optional[Tuple[float, float]]]:
    """Replicates the wisp push delta logic used in the original controller.

    Returns ((dx, dy), new_last_center). Caller is responsible for storing
    the returned last center for subsequent frames.
    """
    if player is None:
        return (0.0, 0.0), last_player_center

    p_model = getattr(player, "model", None)
    if p_model is None:
        return (0.0, 0.0), last_player_center

    rect = getattr(p_model, "feet_rect", None)
    if rect is None:
        rect = getattr(p_model, "rect", None)
    if rect is None:
        return (0.0, 0.0), last_player_center

    player_rect = pygame.Rect(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))
    player_center = (float(player_rect.centerx), float(player_rect.centery))

    if last_player_center is None:
        return (0.0, 0.0), player_center

    player_delta_x = player_center[0] - last_player_center[0]
    player_delta_y = player_center[1] - last_player_center[1]

    wisp_rect = pygame.Rect(
        int(wisp_x + collider_offset[0]),
        int(wisp_y + collider_offset[1]),
        int(collider_size[0]),
        int(collider_size[1]),
    )

    epsilon = 1
    contact_rect = player_rect.inflate(epsilon * 2, epsilon * 2)
    if not contact_rect.colliderect(wisp_rect):
        return (0.0, 0.0), player_center

    if abs(player_delta_x) <= 1e-6 and abs(player_delta_y) <= 1e-6:
        return (0.0, 0.0), player_center

    limit = max(0.0, float(wisp_speed_px_s) * float(dt))
    mag_sq = player_delta_x * player_delta_x + player_delta_y * player_delta_y
    if mag_sq > 1e-12:
        mag = mag_sq ** 0.5
        if mag > limit and limit > 0.0:
            scale = limit / mag
            return (player_delta_x * scale, player_delta_y * scale), player_center
    return (player_delta_x, player_delta_y), player_center

