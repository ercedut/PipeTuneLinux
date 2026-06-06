"""Data models for WirePlumber and routing diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ServiceStatus:
    name: str
    active: bool | None  # None = unknown/not-checkable
    details: str = ""


@dataclass(slots=True)
class AudioDevice:
    node_id: str
    name: str
    description: str
    is_default: bool = False
    device_type: str = ""  # "sink", "source", "card"
    profile: str = ""
    is_bluetooth: bool = False
    bluetooth_profile: str = ""  # "a2dp", "hfp", "hsp", "unknown"


@dataclass(slots=True)
class WirePlumberAuditReport:
    passed: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    services: list[ServiceStatus] = field(default_factory=list)
    default_sink: str = ""
    default_source: str = ""
    sink_count: int = 0
    source_count: int = 0
    card_count: int = 0
    collected_at: str = ""

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


@dataclass(slots=True)
class RouteAuditReport:
    passed: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    default_sink: str = ""
    default_source: str = ""
    sink_count: int = 0
    source_count: int = 0
    has_virtual_sinks: bool = False
    has_pipetune_configs: bool = False
    bluetooth_hfp_suspected: bool = False
    collected_at: str = ""

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"
