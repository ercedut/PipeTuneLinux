"""Typed models for profile safety and activation preflight."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_PROFILE_TYPES = {"headphone", "laptop_speaker", "microphone", "bluetooth", "system", "unknown"}


@dataclass(slots=True)
class ProfileSafetyMetadata:
    profile_id: str
    profile_name: str
    profile_type: str
    target_device_name: str | None
    target_device_type: str | None
    generated_by: str
    generator_version: str
    source_format: str | None
    source_file: str | None
    created_at: str
    preamp_db: float | None
    max_positive_gain_db: float | None
    max_negative_gain_db: float | None
    filter_count: int
    enabled_filter_count: int
    requires_manual_output_confirmation: bool
    auto_apply_safe: bool
    hardware_quirk_sensitive: bool
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HardwareQuirkMetadata:
    quirk_detected: bool
    quirk_type: str | None
    auto_switch_safe: bool
    built_in_microphone_reliable: bool | None
    requires_manual_output_confirmation: bool
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ActivationReadiness:
    status: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProfileSafetyCheck:
    file_path: str
    exists: bool
    readable: bool
    appears_generated_by_pipetune: bool | None
    filter_chain_config: bool | None
    filter_count: int
    manifest_present: bool
    preamp_metadata: str
    safety_status: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    profile_type: str = "unknown"


@dataclass(slots=True)
class ProfilePreflightResult:
    profile_name: str
    profile_type: str
    config_path: str
    manifest_path: str | None
    manifest_present: bool
    hardware_quirk: HardwareQuirkMetadata
    readiness: ActivationReadiness
