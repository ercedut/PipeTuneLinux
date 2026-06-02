"""Tolerant parsers for read-only capture gain command output."""

from __future__ import annotations

import re

from pipetune.gain.gain_models import MixerControl, SourceVolume, WpctlVolume

_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")
_DB_RE = re.compile(r"\[?\s*([+-]?\d+(?:[\.,]\d+)?)\s*dB\s*\]?", re.IGNORECASE)
_CHANNEL_DB_RE = re.compile(r"\d+\s*/\s*\d{1,3}\s*%\s*/\s*([+-]?\d+(?:[\.,]\d+)?)\s*dB", re.IGNORECASE)
_CHANNEL_PERCENT_RE = re.compile(r"([^:,\n]+):\s*\d+\s*/\s*(\d{1,3})\s*%")
_SCONTROL_RE = re.compile(r"Simple mixer control '([^']+)'")


def parse_pactl_source_volume(text: str) -> SourceVolume:
    percentages = [int(value) for value in _PERCENT_RE.findall(text)]
    db_values = [_parse_float(value) for value in _CHANNEL_DB_RE.findall(text)]
    channels: dict[str, int] = {}

    for match in _CHANNEL_PERCENT_RE.finditer(text):
        channel_name = match.group(1).split(":")[-1].strip().lower()
        if channel_name and not channel_name.isdigit():
            channels[channel_name] = int(match.group(2))

    return SourceVolume(percentages=percentages, db_values=db_values, channels=channels)


def parse_pactl_source_mute(text: str) -> bool | None:
    lowered = text.strip().lower()
    value = lowered.split(":", 1)[1].strip() if ":" in lowered else lowered
    first_word = value.split()[0] if value.split() else ""

    if first_word in {"yes", "evet", "true", "1", "muted"}:
        return True
    if first_word in {"no", "hayir", "hayır", "false", "0", "unmuted"}:
        return False
    return None


def parse_wpctl_volume(text: str) -> WpctlVolume:
    match = re.search(r"Volume:\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
    volume = float(match.group(1)) if match else None
    lowered = text.lower()

    muted: bool | None = None
    if "[muted]" in lowered or "muted: yes" in lowered:
        muted = True
    elif "[unmuted]" in lowered or "muted: no" in lowered:
        muted = False

    return WpctlVolume(volume=volume, muted=muted)


def parse_simple_controls(text: str) -> list[str]:
    return [match.strip() for match in _SCONTROL_RE.findall(text)]


def parse_amixer_controls(text: str) -> list[MixerControl]:
    controls: list[MixerControl] = []
    blocks = re.split(r"\n(?=Simple mixer control ')", text)

    for block in blocks:
        match = _SCONTROL_RE.search(block)
        if not match:
            continue

        lowered = block.lower()
        states = re.findall(r"\[(on|off)\]", block, re.IGNORECASE)
        capture_enabled: bool | None = None
        if "[capture]" in lowered:
            capture_enabled = True
        elif "[nocapture]" in lowered:
            capture_enabled = False

        controls.append(
            MixerControl(
                name=match.group(1).strip(),
                percentages=[int(value) for value in _PERCENT_RE.findall(block)],
                db_values=[_parse_float(value) for value in _DB_RE.findall(block)],
                states=[state.lower() for state in states],
                capture_enabled=capture_enabled,
                raw=block.strip(),
            )
        )

    return controls


def is_capture_related_control(name: str) -> bool:
    lowered = name.lower()
    hints = ("capture", "mic", "internal mic", "mic boost", "digital", "input source", "adc", "boost")
    return any(hint in lowered for hint in hints)


def _parse_float(value: str) -> float:
    return float(value.replace(",", "."))
