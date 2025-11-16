from __future__ import annotations

from systems.interactibles.types import InteractibleTarget

WISP_DIALOGUE_ID = "wisp_dialogue"


def start_wisp_dialogue(play_state, target: InteractibleTarget) -> None:
    dialogue = getattr(play_state, "dialogue_manager", None)
    if dialogue is None:
        raise RuntimeError("Dialogue manager is required for wisp dialogue")
    if getattr(dialogue, "is_active", False):
        raise RuntimeError("Dialogue already active while triggering wisp dialogue")

    display = getattr(play_state, "display", None)
    if display is None:
        raise RuntimeError("PlayState missing display for wisp dialogue")

    base_width = getattr(display, "base_width", None)
    base_height = getattr(display, "base_height", None)
    if base_width is None or base_height is None:
        raise RuntimeError("Display missing dimensions for wisp dialogue")
    surface_size = (int(base_width), int(base_height))

    dialogue.set_surface_size(surface_size)
    if target.kind == "mob" and target.mob is not None:
        spec = getattr(target.mob, "spec", None)
        species_id = getattr(spec, "id", "wisp")
        metadata = {
            "interactible_id": species_id,
            "dataset": "mobs",
            "mob_species": species_id,
        }
    elif target.descriptor is not None:
        metadata = {
            "interactible_id": target.descriptor.object_id,
            "dataset": target.descriptor.dataset,
            "mob_species": "wisp",
        }
    else:
        metadata = {"mob_species": "wisp"}
    dialogue.start_dialogue(WISP_DIALOGUE_ID, metadata=metadata)
