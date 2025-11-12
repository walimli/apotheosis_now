from __future__ import annotations

import json
import os
from collections.abc import Iterable
from typing import Dict, List

import pygame


class MobAssetProvider:
    """
    Loads and serves mob animation frames via one or more asset registry files.

    No fallbacks:
    - load_registry() must be called before get_frames().
    - All referenced asset keys and files must exist.
    """

    def __init__(self) -> None:
        self._loaded: bool = False
        self._asset_keys: Dict[str, str] = {}
        self._asset_files: Dict[str, str] = {}
        self._animation_groups: Dict[str, List[str]] = {}
        self._frames_cache: Dict[str, List[pygame.Surface]] = {}
        self._registry_paths: List[str] = []

    # --- Public API ---
    def load_registry(self, registry_path: str | Iterable[str] | None = None) -> None:
        """Load one or more mob asset registries."""

        paths = self._resolve_registry_paths(registry_path)

        self._asset_keys = {}
        self._asset_files = {}
        self._animation_groups = {}
        self._frames_cache.clear()
        self._registry_paths = paths

        project_root = self._project_root()
        for path in paths:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert isinstance(data, dict), f"{path} must be a JSON object"
            assert (
                data.get("registry_type") == "mob_assets"
            ), f"Invalid registry_type in {path}"

            base_path = data.get("base_path")
            assert (
                isinstance(base_path, str) and base_path
            ), f"Missing/invalid base_path in {path}"
            asset_keys = data.get("asset_keys")
            assert (
                isinstance(asset_keys, dict) and asset_keys
            ), f"Missing/invalid asset_keys in {path}"
            animation_groups = data.get("animation_groups")
            assert (
                isinstance(animation_groups, dict) and animation_groups
            ), f"Missing/invalid animation_groups in {path}"

            abs_base = os.path.abspath(os.path.join(project_root, base_path))

            for raw_key, raw_rel in asset_keys.items():
                key = str(raw_key)
                rel = str(raw_rel)
                abs_path = os.path.abspath(os.path.join(abs_base, rel))
                if key in self._asset_files:
                    raise KeyError(f"Duplicate mob asset key {key!r} across registries")
                self._asset_keys[key] = os.path.join(base_path, rel).replace("\\", "/")
                self._asset_files[key] = abs_path

            for group_key, keys in animation_groups.items():
                gk = str(group_key)
                if gk in self._animation_groups:
                    raise KeyError(
                        f"Duplicate animation group {gk!r} across registries"
                    )
                assert (
                    isinstance(keys, list) and keys
                ), f"animation group {gk!r} must be a non-empty list"
                self._animation_groups[gk] = [str(k) for k in keys]

        self._loaded = True

    def get_frames(self, group_key: str) -> List[pygame.Surface]:
        assert self._loaded, "MobAssetProvider: registry not loaded"
        if group_key in self._frames_cache:
            return self._frames_cache[group_key]

        keys = self._animation_groups.get(group_key)
        if keys is None:
            raise KeyError(f"Unknown animation group {group_key!r}")

        frames: List[pygame.Surface] = []
        for key in keys:
            abs_path = self._asset_files.get(key)
            if abs_path is None:
                raise KeyError(
                    f"animation_groups[{group_key!r}] references unknown asset key {key!r}"
                )
            if not os.path.isfile(abs_path):
                raise FileNotFoundError(f"Mob frame not found: {abs_path}")
            surf = pygame.image.load(abs_path).convert_alpha()
            frames.append(surf)

        self._frames_cache[group_key] = frames
        return frames

    # --- Helpers ---
    def _resolve_registry_paths(
        self, registry_path: str | Iterable[str] | None
    ) -> List[str]:
        if registry_path is None:
            return self._discover_registry_files()

        if isinstance(registry_path, str):
            candidates = [registry_path]
        else:
            candidates = list(registry_path)
            if not candidates:
                raise ValueError(
                    "registry_path iterable must contain at least one path"
                )

        resolved: List[str] = []
        project_root = self._project_root()
        for candidate in candidates:
            path = candidate
            if not os.path.isabs(path):
                candidate_path = os.path.join(project_root, path)
                if os.path.isfile(candidate_path):
                    path = candidate_path
                else:
                    path = os.path.abspath(path)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Mob asset registry not found: {candidate}")
            resolved.append(os.path.abspath(path))

        return resolved

    def _discover_registry_files(self) -> List[str]:
        data_dir = os.path.join(self._project_root(), "data", "mobs")
        if not os.path.isdir(data_dir):
            raise FileNotFoundError(f"Mob data directory not found: {data_dir}")

        paths: List[str] = []
        for name in sorted(os.listdir(data_dir)):
            if name == "mob_asset_registry.json" or name.endswith("_asset_registry.json"):
                full_path = os.path.join(data_dir, name)
                if os.path.isfile(full_path):
                    paths.append(full_path)

        if not paths:
            raise FileNotFoundError(f"No mob asset registries found in {data_dir}")

        return paths

    def _project_root(self) -> str:
        here = os.path.dirname(__file__)
        # systems/asset_loader -> project root is two levels up from asset_loader
        return os.path.abspath(os.path.join(here, os.pardir, os.pardir))


