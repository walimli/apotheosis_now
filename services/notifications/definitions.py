"""Loadable notification definitions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NotificationDefinition:
    """Single notification template loaded from JSON."""

    id: str
    title: str
    body: str
    trigger: str
    font: str
    title_font_size: int
    body_font_size: int
    wrap_width: int
    text_color: tuple[int, int, int]
    font_size: int
    x_offset: int
    y_offset: int

    @classmethod
    def from_path(cls, path: Path) -> "NotificationDefinition":
        """Create a definition from a JSON file."""
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        required = {
            "Id",
            "Title",
            "Body",
            "Trigger",
            "Font",
            "Title_Font_Size",
            "Body_Font_Size",
            "Wrap_Width",
            "Text_Color",
            "Font_Size",
            "X_offset",
            "Y_offset",
        }
        missing = required.difference(data)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Notification definition missing fields: {names}")

        text_color = cls._coerce_color(data["Text_Color"])
        return cls(
            id=str(data["Id"]),
            title=str(data["Title"]),
            body=str(data["Body"]),
            trigger=str(data["Trigger"]),
            font=str(data["Font"]),
            title_font_size=int(data["Title_Font_Size"]),
            body_font_size=int(data["Body_Font_Size"]),
            wrap_width=int(data["Wrap_Width"]),
            text_color=text_color,
            font_size=int(data["Font_Size"]),
            x_offset=int(data["X_offset"]),
            y_offset=int(data["Y_offset"]),
        )

    @staticmethod
    def _coerce_color(raw: Any) -> tuple[int, int, int]:
        """Validate RGB tuples."""
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            raise ValueError("Text_Color must be a sequence of three integers")
        rgb = tuple(int(channel) for channel in raw)
        for channel in rgb:
            if channel < 0 or channel > 255:
                raise ValueError("Text_Color components must be between 0 and 255")
        return rgb


__all__ = ["NotificationDefinition"]
