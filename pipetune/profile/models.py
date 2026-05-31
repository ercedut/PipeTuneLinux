"""Profile models for AutoEQ parsing and PipeWire generation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class EqFilter:
    index: int
    enabled: bool
    filter_type: str
    frequency_hz: float
    gain_db: float
    q: float


@dataclass(slots=True)
class AudioProfile:
    name: str
    preamp_db: float | None
    filters: list[EqFilter]
    source_format: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProfileValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


@dataclass(slots=True)
class AutoEqParseResult:
    profile: AudioProfile
    errors: list[str]
