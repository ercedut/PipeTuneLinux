"""Activation install and rollback models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class InstallManifest:
    install_id: str
    profile_name: str
    profile_id: str
    source_config_path: str
    installed_config_path: str
    backup_path: str | None
    installed_at: str
    installed_by: str
    pipetune_version: str
    preflight_status: str
    hardware_quirk_confirmed: bool
    user_level: bool
    source_sha256: str
    installed_sha256: str
    manifest_schema_version: str
    rollback_status: str
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class InstallDryRun:
    source_config_path: str
    destination_path: str
    manifest_path: str
    backup_would_be_created: bool
    preflight_status: str
    hardware_quirk_confirmation_required: bool
    install_allowed_with_current_flags: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InstallResult:
    success: bool
    exit_code: int
    profile_name: str | None
    install_id: str | None
    destination_path: str | None
    manifest_path: str | None
    backup_path: str | None
    backup_created: bool
    preflight_status: str | None
    hardware_quirk_confirmed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RollbackResult:
    success: bool
    exit_code: int
    install_id: str | None
    removed_config_path: str | None
    restored_backup: bool
    rollback_log_path: str | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
