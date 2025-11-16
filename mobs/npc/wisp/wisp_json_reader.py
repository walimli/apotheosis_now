from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional, Union

from systems.mobs.core.species_loader import MobSpec, load_spec_from_file

PathLike = Union[str, Path]


@dataclass
class WispSpec(MobSpec):
    """MobSpec extension that preserves the interaction event metadata."""

    interaction_event: Optional[str] = None


def load_wisp_spec(path: PathLike) -> WispSpec:
    """Load the wisp mob specification, including its interaction event."""

    base_spec = load_spec_from_file(str(path))
    interaction_event = _read_interaction_event(path)

    base_kwargs = {field.name: getattr(base_spec, field.name) for field in fields(MobSpec)}

    return WispSpec(
        **base_kwargs,
        interaction_event=interaction_event,
    )


def _read_interaction_event(path: PathLike) -> Optional[str]:
    raw_path = Path(path)
    with raw_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    event = payload.get("interaction_event")
    if event is None:
        return None
    if not isinstance(event, str):
        raise TypeError("interaction_event must be a string if provided")
    event = event.strip()
    return event or None
