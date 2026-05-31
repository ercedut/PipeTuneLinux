"""Data models for hardware quirk audits."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PinConfigSnapshot:
    path: str
    exists: bool
    readable: bool
    non_empty: bool
    error: str | None = None


@dataclass(slots=True)
class HdaAuditResult:
    codec_files: list[str]
    init_pin_configs: list[PinConfigSnapshot]
    driver_pin_configs: list[PinConfigSnapshot]
    user_pin_configs: list[PinConfigSnapshot]
    user_pin_overrides_present: bool | None
    retask_reference_hits: list[str]
    retask_reference_search_errors: list[str]
    retask_reference_search_status: str
    retask_files_scanned: int
    retask_files_skipped: int
    alsa_cards_count: int
    alsa_capture_devices_count: int
    ucm2_directory_exists: bool
    manual_hda_retask_detected: bool
    manual_hda_retask_suspected: bool
    safety_recommendation: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MicAuditResult:
    alsa_capture_devices_count: int
    source_count: int | None
    default_source: str | None
    default_source_muted: bool | None
    default_source_state: str | None
    internal_mic_route_visible: str
    capture_test_performed: bool
    microphone_status: str
    safety_recommendation: str
    warnings: list[str] = field(default_factory=list)
