from __future__ import annotations

from typing import Optional, Sequence, Tuple

import pygame

from .widgets import IconButton, SystemButton


class LayoutManager:
    def __init__(self) -> None:
        self.square_rect: Optional[pygame.Rect] = None
        self.tall_rect: Optional[pygame.Rect] = None
        self._last_layout_size: Optional[Tuple[int, int]] = None

    def reset(self) -> None:
        self.square_rect = None
        self.tall_rect = None
        self._last_layout_size = None

    def ensure(
        self,
        size: Tuple[int, int],
        square_card: pygame.Surface,
        tall_card: pygame.Surface,
        system_button: SystemButton,
        icon_buttons: Sequence[IconButton],
    ) -> None:
        if self._last_layout_size == size:
            return
        width, height = size
        square_rect = square_card.get_rect()
        tall_rect = tall_card.get_rect()
        gap = 48
        total_width = square_rect.width + gap + tall_rect.width
        if total_width > width:
            gap = max(24, gap - (total_width - width))
            total_width = square_rect.width + gap + tall_rect.width
        start_x = max(0, (width - total_width) // 2)
        center_y = height // 2
        square_rect.topleft = (
            start_x,
            max(0, center_y - square_rect.height // 2),
        )
        tall_left = square_rect.right + gap
        if tall_left + tall_rect.width > width:
            tall_left = max(square_rect.right + 12, width - tall_rect.width)
        tall_rect.topleft = (
            tall_left,
            max(0, center_y - tall_rect.height // 2),
        )

        button_rect = system_button.rect.copy()
        button_gap = 24
        button_rect.centery = square_rect.centery
        button_rect.right = square_rect.left - button_gap
        system_button.set_rect(button_rect)

        if not icon_buttons:
            raise RuntimeError("No icon buttons loaded")
        icon_w = icon_buttons[0].width
        icon_h = icon_buttons[0].height
        side_margin = max(40, (square_rect.width - icon_w * 3) // 4)
        vertical_margin = max(40, (square_rect.height - icon_h * 2) // 3)
        row_gap = vertical_margin
        first_row_center_y = square_rect.top + vertical_margin + icon_h // 2
        second_row_center_y = first_row_center_y + icon_h + row_gap
        col_centers = []
        for idx in range(3):
            cx = (
                square_rect.left
                + side_margin
                + icon_w // 2
                + idx * (icon_w + side_margin)
            )
            col_centers.append(cx)

        for index, icon in enumerate(icon_buttons):
            col = index % 3
            row = index // 3
            cy = first_row_center_y if row == 0 else second_row_center_y
            icon.set_center((col_centers[col], cy))

        self.square_rect = square_rect
        self.tall_rect = tall_rect
        self._last_layout_size = size


__all__ = ["LayoutManager"]
