from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from systems.collision.json_validator import assert_offset, validate_aabb
from systems.drops.specs import DropSpec


CollisionPolygon = Optional[Sequence[Tuple[float, float]]]


@dataclass(frozen=True)
class CollisionAABB:
    width: float
    height: float
    offset_x: float
    offset_y: float


@dataclass(frozen=True)
class AnimationSheetSpec:
    sheet_path: str
    columns: int
    rows: int
    frames: Optional[int] = None
    start_index: int = 0

    @property
    def total_slots(self) -> int:
        return self.columns * self.rows

    @property
    def effective_frames(self) -> int:
        if self.frames is not None:
            return max(0, min(self.frames, self.total_slots))
        return self.total_slots


@dataclass(frozen=True)
class PlaceableRecord:
    key: str
    display_name: Optional[str]
    image_path: str
    animation: bool
    animation_sheet: Optional[AnimationSheetSpec]
    scale: float
    z_index: int
    collision_polygon: CollisionPolygon
    collision_mask: Optional[str]
    collision_offsets: Tuple[float, float]
    collision_aabb: CollisionAABB
    dawn_growth: Optional[bool]
    durability_max: Optional[int]
    ysort_anchor_fraction: Optional[float]
    ysort_offset_px: Optional[int]
    drops: Tuple[DropSpec, ...]
    connecting_edges: Tuple[str, ...]
    variant_id: Optional[str]
    protection_radius: Optional[float]
    safe_zone_radius: Optional[float]
    interaction_event: Optional[str]
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class PlaceableDataset:
    name: str
    dataset_type: str
    entries: Tuple[PlaceableRecord, ...]
    order: Tuple[str, ...]
    source_path: Path

    def as_dict(self) -> Dict[str, PlaceableRecord]:
        return {entry.key: entry for entry in self.entries}

    def get(self, key: str) -> PlaceableRecord:
        lookup = self.as_dict()
        if key not in lookup:
            raise KeyError(f"Unknown placeable key '{key}' in dataset '{self.name}'")
        return lookup[key]

    def find_by_variant(self, variant_id: str) -> Optional[PlaceableRecord]:
        for entry in self.entries:
            if entry.variant_id == variant_id:
                return entry
        return None


class PlaceablesJsonReader:
    """Load and normalise placeable definitions from JSON data files."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        root = project_root or Path(__file__).resolve().parents[2]
        self._project_root = Path(root)
        self._data_dir = self._project_root / "data" / "placeables"
        self._cache: Dict[str, PlaceableDataset] = {}

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    def load_dataset(self, name: str) -> PlaceableDataset:
        if name in self._cache:
            return self._cache[name]
        path = self._data_dir / f"{name}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Placeable data file not found: {path}")
        payload = self._read_json(path)
        dataset_type, entries_map = self._normalise_payload(payload)
        records: list[PlaceableRecord] = []
        order: list[str] = []
        for key, raw_entry in entries_map.items():
            record = self._parse_entry(name, key, raw_entry)
            records.append(record)
            order.append(key)
        dataset = PlaceableDataset(
            name=name,
            dataset_type=dataset_type,
            entries=tuple(records),
            order=tuple(order),
            source_path=path,
        )
        self._cache[name] = dataset
        return dataset

    def load_all(self) -> Dict[str, PlaceableDataset]:
        datasets: Dict[str, PlaceableDataset] = {}
        for file_path in sorted(self._data_dir.glob("*.json")):
            name = file_path.stem
            datasets[name] = self.load_dataset(name)
        return datasets

    def _read_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _normalise_payload(
        self, payload: Any
    ) -> Tuple[str, "dict[str, dict[str, Any]]"]:
        if not isinstance(payload, dict):
            raise TypeError("Placeable data must be a JSON object at the top level")
        dataset_type = "stages"
        entries_map: Dict[str, Dict[str, Any]]
        if len(payload) == 1:
            sole_key, sole_value = next(iter(payload.items()))
            if isinstance(sole_value, dict) and sole_value and all(
                isinstance(value, dict) for value in sole_value.values()
            ):
                dataset_type = "variants"
                entries_map = {str(k): dict(v) for k, v in sole_value.items()}
            else:
                entries_map = {sole_key: dict(sole_value)}
        else:
            entries_map = {str(k): dict(v) for k, v in payload.items()}
        return dataset_type, entries_map

    def _parse_entry(
                self, dataset_name: str, entry_key: str, raw: Mapping[str, Any]
    ) -> PlaceableRecord:
        if not isinstance(raw, Mapping):
            raise TypeError(
                f"Placeable '{entry_key}' in dataset '{dataset_name}' must be an object"
            )

        display_name = self._get_optional_str(raw, "display_name")
        image_path = self._require_str(raw, "image_path", dataset_name, entry_key)
        animation = self._coerce_bool(raw.get("animation", False))
        sheet_spec = self._parse_animation_sheet(raw.get("animation_sheet"))
        scale = self._coerce_float(raw.get("scale", 1.0))
        z_index = self._coerce_int(raw.get("z_index", 0))
        collision_polygon, collision_mask = self._parse_collision(raw)
        offsets = self._parse_offsets(raw.get("collision_offsets"))
        collision_aabb = self._parse_collision_aabb(raw, collision_polygon)
        dawn_growth = self._coerce_optional_bool(raw.get("dawn_growth"))
        durability_max = self._coerce_optional_int(raw.get("durability_max"))
        ysort_anchor = self._coerce_optional_float(raw.get("ysort_anchor_fraction"))
        ysort_offset = self._coerce_optional_int(raw.get("ysort_offset_px"))
        drops = self._parse_drops(raw)
        connecting_edges = self._parse_str_sequence(raw.get("connecting_edges"))
        variant_id = self._get_optional_str(raw, "id")
        protection_radius = self._parse_protection_radius(raw.get("protection"))
        safe_zone_radius = self._parse_safe_zone_radius(raw.get("safe_zone"))
        interaction_event = self._get_optional_str(raw, "interaction_event")

        consumed_keys = {
            "display_name",
            "image_path",
            "animation",
            "animation_sheet",
            "scale",
            "z_index",
            "collision_polygon",
            "collision_offsets",
            "dawn_growth",
            "durability_max",
            "ysort_anchor_fraction",
            "ysort_offset_px",
            "drops",
            "drop",
            "connecting_edges",
            "id",
            "protection",
            "safe_zone",
            "interaction_event",
        }
        metadata = {
            key: value
            for key, value in raw.items()
            if key not in consumed_keys
        }

        return PlaceableRecord(
            key=entry_key,
            display_name=display_name,
            image_path=str(image_path),
            animation=animation,
            animation_sheet=sheet_spec,
            scale=scale,
            z_index=z_index,
            collision_polygon=collision_polygon,
            collision_mask=collision_mask,
            collision_offsets=offsets,
            collision_aabb=collision_aabb,
            dawn_growth=dawn_growth,
            durability_max=durability_max,
            ysort_anchor_fraction=ysort_anchor,
            ysort_offset_px=ysort_offset,
            drops=drops,
            connecting_edges=connecting_edges,
            variant_id=variant_id,
            protection_radius=protection_radius,
            safe_zone_radius=safe_zone_radius,
            interaction_event=interaction_event,
            metadata=metadata,
        )

    def _parse_collision(
        self, raw: Mapping[str, Any]
    ) -> Tuple[CollisionPolygon, Optional[str]]:
        poly_data = raw.get("collision_polygon")
        if poly_data is None:
            return None, None
        if isinstance(poly_data, str):
            return None, poly_data
        if isinstance(poly_data, Sequence):
            polygon: list[Tuple[float, float]] = []
            for point in poly_data:
                if (
                    not isinstance(point, Sequence)
                    or len(point) != 2
                    or not all(isinstance(coord, (int, float)) for coord in point)
                ):
                    raise ValueError(
                        "collision_polygon must be a sequence of [x, y] coordinate pairs"
                    )
                x, y = float(point[0]), float(point[1])
                polygon.append((x, y))
            return tuple(polygon), None
        raise TypeError("collision_polygon must be a string or list of coordinate pairs")

    def _parse_offsets(self, value: Any) -> Tuple[float, float]:
        if not isinstance(value, Mapping):
            return (0.0, 0.0)
        x = self._coerce_float(value.get("x", 0.0))
        y = self._coerce_float(value.get("y", 0.0))
        return (x, y)

    def _parse_collision_aabb(
        self,
        raw: Mapping[str, Any],
        polygon: CollisionPolygon,
    ) -> CollisionAABB:
        value = raw.get("collision_aabb")
        context = f"collision_aabb for '{raw.get('display_name') or raw.get('image_path') or 'unknown'}'"
        if isinstance(value, Mapping):
            width = self._coerce_float(value.get("width_px", 0.0))
            height = self._coerce_float(value.get("height_px", 0.0))
            offset_x = self._coerce_float(value.get("offset_x", 0.0))
            offset_y = self._coerce_float(value.get("offset_y", 0.0))
            validate_aabb(width, height, context)
            assert_offset(offset_x, "offset_x", context)
            assert_offset(offset_y, "offset_y", context)
            return CollisionAABB(width=width, height=height, offset_x=offset_x, offset_y=offset_y)

        if polygon and len(polygon) >= 1:
            xs = [float(point[0]) for point in polygon]
            ys = [float(point[1]) for point in polygon]
            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)
            width = max(0.0, max_x - min_x)
            height = max(0.0, max_y - min_y)
            if width > 0.0 and height > 0.0:
                validate_aabb(width, height, context)
                assert_offset(min_x, "offset_x", context)
                assert_offset(min_y, "offset_y", context)
                return CollisionAABB(width=width, height=height, offset_x=min_x, offset_y=min_y)

        # Fallback: single tile footprint centred on origin.
        width = 64.0
        height = 64.0
        validate_aabb(width, height, context)
        return CollisionAABB(width=width, height=height, offset_x=0.0, offset_y=0.0)

    def _parse_drops(self, raw: Mapping[str, Any]) -> Tuple[DropSpec, ...]:
        drops_field = raw.get("drops")
        drop_field = raw.get("drop")
        drops: list[DropSpec] = []
        if isinstance(drops_field, Sequence):
            for entry in drops_field:
                spec = self._parse_drop(entry)
                if spec:
                    drops.append(spec)
        elif isinstance(drops_field, Mapping):
            spec = self._parse_drop(drops_field)
            if spec:
                drops.append(spec)
        if drop_field and not drops:
            spec = self._parse_drop(drop_field)
            if spec:
                drops.append(spec)
        return tuple(drops)

    def _parse_drop(self, value: Any) -> Optional[DropSpec]:
        if not isinstance(value, Mapping):
            return None
        item_id = self._get_optional_str(value, "item")
        if not item_id:
            return None
        qty_min = self._coerce_int(value.get("qty_min", 1))
        qty_max = self._coerce_int(value.get("qty_max", qty_min))
        chance = self._coerce_float(value.get("chance", 1.0))
        spec = DropSpec(item_id=item_id, qty_min=qty_min, qty_max=qty_max, chance=chance)
        return spec.normalized()

    def _parse_str_sequence(self, value: Any) -> Tuple[str, ...]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            return tuple()
        return tuple(str(part) for part in value)

    def _parse_protection_radius(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Mapping):
            radius = value.get("radius")
        else:
            radius = value
        if radius is None:
            return None
        return float(radius)

    def _parse_safe_zone_radius(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Mapping):
            radius = value.get("radius")
        else:
            radius = value
        if radius is None:
            return None
        return float(radius)

    def _require_str(
        self, raw: Mapping[str, Any], key: str, dataset: str, entry: str
    ) -> str:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"'{key}' is required for placeable '{entry}' in dataset '{dataset}'"
            )
        return value.strip()

    def _get_optional_str(
        self, raw: Mapping[str, Any], key: str
    ) -> Optional[str]:
        value = raw.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None

    def _coerce_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "yes", "1"}:
                return True
            if lowered in {"false", "no", "0"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _coerce_optional_bool(self, value: Any) -> Optional[bool]:
        if value is None:
            return None
        return self._coerce_bool(value)

    def _coerce_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        return int(value)

    def _coerce_optional_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        return self._coerce_int(value)

    def _coerce_float(self, value: Any) -> float:
        if isinstance(value, bool):
            return float(int(value))
        return float(value)

    def _coerce_optional_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        return self._coerce_float(value)

    def _parse_animation_sheet(self, value: Any) -> Optional[AnimationSheetSpec]:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise TypeError("animation_sheet must be an object if provided")
        sheet_path = value.get("sheet")
        if not isinstance(sheet_path, str) or not sheet_path.strip():
            raise ValueError("animation_sheet.sheet must be a non-empty string")
        columns = value.get("columns")
        rows = value.get("rows")
        if not isinstance(columns, (int, float)) or not isinstance(rows, (int, float)):
            raise ValueError("animation_sheet columns and rows must be numeric")
        columns = int(columns)
        rows = int(rows)
        if columns <= 0 or rows <= 0:
            raise ValueError("animation_sheet columns and rows must be positive")
        frames = value.get("frames")
        if frames is not None:
            frames = int(frames)
            if frames < 0:
                raise ValueError("animation_sheet.frames must be non-negative")
        start_index = int(value.get("start_index", 0))
        if start_index < 0:
            raise ValueError("animation_sheet.start_index must be non-negative")
        return AnimationSheetSpec(
            sheet_path=sheet_path.strip(),
            columns=columns,
            rows=rows,
            frames=frames,
            start_index=start_index,
        )


__all__ = [
    "PlaceablesJsonReader",
    "PlaceableDataset",
    "PlaceableRecord",
    "CollisionAABB",
    "DropSpec",
    "AnimationSheetSpec",
]
