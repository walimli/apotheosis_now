"""Persistence helpers for player progression and known formulas.

These helpers are stubs for future integration. They serialize the
Progression object and the FormulasLibrary known recipe ids to a JSON file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import json

from .progression import Progression
from .formulas import FormulasLibrary


def save_progression(path: Path, progression: Progression, formulas: FormulasLibrary) -> None:
    data = {
        "progression": progression.to_dict(),
        "formulas": formulas.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_progression(path: Path, recipes_path: Path, inventory_path: Path) -> Tuple[Progression, FormulasLibrary]:
    progression = Progression()
    formulas = FormulasLibrary.from_files(recipes_path, inventory_path)
    if not path.exists():
        return progression, formulas
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        prog_blob = data.get("progression", {})
        progression.load_from_dict(prog_blob)
    except Exception:
        # Keep defaults on failure
        pass
    try:
        form_blob = data.get("formulas", {})
        formulas.load_from_dict(form_blob)
    except Exception:
        pass
    return progression, formulas


__all__ = ["save_progression", "load_progression"]

