"""Profile database loader for PipeTune Linux."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.profiles.schema import REQUIRED_METADATA_FIELDS

PROFILES_DB_ROOT = Path(__file__).resolve().parents[2] / "profiles"
EXCLUDED_SUBDIRS = frozenset({"templates"})


@dataclass(slots=True)
class ProfileRecord:
    path: Path
    metadata: dict
    raw: dict
    parse_error: str | None = None

    @property
    def profile_id(self) -> str:
        return self.metadata.get("profile_id", "")

    @property
    def profile_name(self) -> str:
        return self.metadata.get("profile_name", "")

    @property
    def profile_type(self) -> str:
        return self.metadata.get("profile_type", "")

    @property
    def quality_class(self) -> str:
        return self.metadata.get("quality_class", "")

    @property
    def safety_status(self) -> str:
        return self.metadata.get("safety_status", "")

    @property
    def device_vendor(self) -> str:
        return self.metadata.get("device_vendor", "")

    @property
    def device_model(self) -> str:
        return self.metadata.get("device_model", "")

    def has_source(self) -> bool:
        return bool(self.metadata.get("source_url") or self.metadata.get("source_reference"))

    def has_safeguards(self) -> bool:
        sg = self.raw.get("safeguards", {})
        return bool(sg.get("hpf_hz") is not None and sg.get("limiter_ceiling_db") is not None)

    def safeguard_hpf_hz(self) -> float | None:
        return self.raw.get("safeguards", {}).get("hpf_hz")

    def safeguard_limiter_ceiling_db(self) -> float | None:
        return self.raw.get("safeguards", {}).get("limiter_ceiling_db")


def load_all_profiles(db_root: Path | None = None) -> list[ProfileRecord]:
    root = db_root if db_root is not None else PROFILES_DB_ROOT
    profiles: list[ProfileRecord] = []
    if not root.is_dir():
        return profiles
    for toml_path in sorted(root.rglob("*.toml")):
        if any(part in EXCLUDED_SUBDIRS for part in toml_path.relative_to(root).parts):
            continue
        profiles.append(_load_profile(toml_path))
    return profiles


def _load_profile(path: Path) -> ProfileRecord:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        metadata = raw.get("metadata", {})
        return ProfileRecord(path=path, metadata=metadata, raw=raw)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        return ProfileRecord(path=path, metadata={}, raw={}, parse_error=str(exc))
