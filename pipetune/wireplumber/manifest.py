"""WirePlumber rule install manifest persistence."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MANIFEST_SCHEMA_VERSION = "1"


@dataclass(slots=True)
class RuleManifestEntry:
    install_id: str
    rule_id: str
    source_preview_path: str
    installed_path: str
    checksum: str
    status: Literal["active", "rolled_back", "broken"]
    created_at: str
    pipetune_version: str
    rolled_back_at: str = ""

    def as_dict(self) -> dict:
        return {
            "install_id": self.install_id,
            "rule_id": self.rule_id,
            "source_preview_path": self.source_preview_path,
            "installed_path": self.installed_path,
            "checksum": self.checksum,
            "status": self.status,
            "created_at": self.created_at,
            "pipetune_version": self.pipetune_version,
            "rolled_back_at": self.rolled_back_at,
            "safety": {
                "user_level_only": True,
                "system_level": False,
                "restarted_services": False,
                "changed_routing": False,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RuleManifestEntry":
        return cls(
            install_id=data["install_id"],
            rule_id=data["rule_id"],
            source_preview_path=data["source_preview_path"],
            installed_path=data["installed_path"],
            checksum=data["checksum"],
            status=data["status"],
            created_at=data["created_at"],
            pipetune_version=data["pipetune_version"],
            rolled_back_at=data.get("rolled_back_at", ""),
        )


def load_manifest(manifest_path: Path) -> list[RuleManifestEntry]:
    """Load all manifest entries from disk. Returns empty list if file missing or corrupt."""
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return [RuleManifestEntry.from_dict(entry) for entry in data.get("entries", [])]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def save_manifest(manifest_path: Path, entries: list[RuleManifestEntry]) -> None:
    """Persist the manifest entry list atomically."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "entries": [entry.as_dict() for entry in entries],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def get_entry(entries: list[RuleManifestEntry], install_id: str) -> RuleManifestEntry | None:
    """Return the entry with the given install_id, or None."""
    for entry in entries:
        if entry.install_id == install_id:
            return entry
    return None
