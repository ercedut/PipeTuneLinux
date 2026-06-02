"""Models for capture gain audits."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SourceVolume:
    percentages: list[int] = field(default_factory=list)
    db_values: list[float] = field(default_factory=list)
    channels: dict[str, int] = field(default_factory=dict)

    @property
    def primary_percent(self) -> int | None:
        if self.percentages:
            return self.percentages[0]
        return None


@dataclass(slots=True)
class WpctlVolume:
    volume: float | None = None
    muted: bool | None = None


@dataclass(slots=True)
class MixerControl:
    name: str
    percentages: list[int] = field(default_factory=list)
    db_values: list[float] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    capture_enabled: bool | None = None
    raw: str = ""

    @property
    def summary(self) -> str:
        parts: list[str] = []
        if self.percentages:
            parts.append("/".join(f"{value}%" for value in self.percentages))
        if self.db_values:
            parts.append("/".join(f"{value:g} dB" for value in self.db_values))
        if self.states:
            parts.append("/".join(self.states))
        if self.capture_enabled is not None:
            parts.append("cap" if self.capture_enabled else "nocap")
        return ", ".join(parts) if parts else "value unknown"


@dataclass(slots=True)
class GainAudit:
    default_source: str | None
    default_source_muted: bool | None
    pactl_volume: SourceVolume | None
    wpctl_volume: WpctlVolume | None
    mixer_controls: list[MixerControl]
    simple_controls: list[str]
    warnings: list[str] = field(default_factory=list)
