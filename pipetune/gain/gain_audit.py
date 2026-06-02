"""Read-only capture gain audit."""

from __future__ import annotations

from pipetune.collectors.command import run_command
from pipetune.gain.gain_models import GainAudit, MixerControl
from pipetune.gain.gain_parser import (
    is_capture_related_control,
    parse_amixer_controls,
    parse_pactl_source_mute,
    parse_pactl_source_volume,
    parse_simple_controls,
    parse_wpctl_volume,
)
from pipetune.gain.gain_recommendations import interpret_gain_risks


def collect_gain_audit() -> GainAudit:
    warnings: list[str] = []

    default_source_result = run_command(["pactl", "get-default-source"])
    default_source = _first_stdout_line(default_source_result.stdout) if _command_ok(default_source_result) else None
    if not default_source:
        warnings.append("Default Pulse/PipeWire source could not be read.")

    pactl_volume_result = run_command(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"])
    pactl_volume = parse_pactl_source_volume(pactl_volume_result.stdout) if _command_ok(pactl_volume_result) else None
    if pactl_volume is None:
        warnings.append("pactl source volume is unavailable.")

    pactl_mute_result = run_command(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"])
    default_source_muted = parse_pactl_source_mute(pactl_mute_result.stdout) if _command_ok(pactl_mute_result) else None
    if default_source_muted is None:
        warnings.append("pactl source mute state is unavailable or unknown.")

    wpctl_volume_result = run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
    wpctl_volume = parse_wpctl_volume(wpctl_volume_result.stdout) if _command_ok(wpctl_volume_result) else None
    if wpctl_volume is None:
        warnings.append("wpctl source volume is unavailable.")

    simple_controls_result = run_command(["amixer", "-c", "0", "scontrols"])
    simple_controls = parse_simple_controls(simple_controls_result.stdout) if _command_ok(simple_controls_result) else []
    if not simple_controls:
        warnings.append("ALSA simple mixer controls are unavailable for card 0.")

    amixer_result = run_command(["amixer", "-c", "0"])
    all_controls = parse_amixer_controls(amixer_result.stdout) if _command_ok(amixer_result) else []
    if not all_controls:
        warnings.append("Detailed ALSA mixer state is unavailable for card 0.")

    capture_related = [control for control in all_controls if is_capture_related_control(control.name)]

    return GainAudit(
        default_source=default_source,
        default_source_muted=default_source_muted,
        pactl_volume=pactl_volume,
        wpctl_volume=wpctl_volume,
        mixer_controls=capture_related,
        simple_controls=simple_controls,
        warnings=warnings,
    )


def render_gain_audit(audit: GainAudit) -> str:
    detected = _detected_controls(audit.mixer_controls)
    lines = [
        "PipeTune Capture Gain Audit",
        "",
        "Default source:",
        f"* Name: {audit.default_source or 'unknown'}",
        f"* Mute: {_bool_label(audit.default_source_muted)}",
        f"* Pulse/PipeWire volume: {_pactl_volume_label(audit)}",
        f"* Pulse/PipeWire dB: {_pactl_db_label(audit)}",
        f"* wpctl volume: {_wpctl_volume_label(audit)}",
        "",
        "ALSA capture controls:",
        f"* Capture: {_control_label(detected.get('capture'))}",
        f"* Mic Boost: {_control_label(detected.get('mic boost'))}",
        f"* Internal Mic Boost: {_control_label(detected.get('internal mic boost'))}",
        f"* Digital: {_control_label(detected.get('digital'))}",
        f"* Input Source: {_control_label(detected.get('input source'))}",
        f"* ADC: {_control_label(detected.get('adc'))}",
        "",
        "Risk interpretation:",
    ]
    lines.extend(f"* {risk}" for risk in interpret_gain_risks(audit))

    if audit.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"* {warning}" for warning in audit.warnings)

    lines.extend(
        [
            "",
            "Recommendation:",
            "* Manual tuning required. Do not store ALSA state until stable values are confirmed.",
            "* This v0.2.4 audit uses ALSA card 0 as a conservative first implementation when no better card mapping is available.",
            "",
            "No system configuration was modified.",
        ]
    )
    return "\n".join(lines)


def _command_ok(result) -> bool:
    return result.available and result.exit_code == 0


def _first_stdout_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _bool_label(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _pactl_volume_label(audit: GainAudit) -> str:
    if not audit.pactl_volume or audit.pactl_volume.primary_percent is None:
        return "unknown"
    return f"{audit.pactl_volume.primary_percent}%"


def _pactl_db_label(audit: GainAudit) -> str:
    if not audit.pactl_volume or not audit.pactl_volume.db_values:
        return "unknown"
    return f"{audit.pactl_volume.db_values[0]:g} dB"


def _wpctl_volume_label(audit: GainAudit) -> str:
    if not audit.wpctl_volume or audit.wpctl_volume.volume is None:
        return "unknown"
    muted = " muted" if audit.wpctl_volume.muted else ""
    return f"{audit.wpctl_volume.volume:.2f}{muted}"


def _detected_controls(controls: list[MixerControl]) -> dict[str, MixerControl]:
    detected: dict[str, MixerControl] = {}
    priority = [
        ("internal mic boost", "internal mic boost"),
        ("mic boost", "mic boost"),
        ("input source", "input source"),
        ("capture", "capture"),
        ("digital", "digital"),
        ("adc", "adc"),
    ]
    for control in controls:
        lowered = control.name.lower()
        for key, fragment in priority:
            if fragment in lowered and key not in detected:
                detected[key] = control
    return detected


def _control_label(control: MixerControl | None) -> str:
    if control is None:
        return "unknown"
    return f"detected, current value {control.summary}"
