"""Manual gain recommendations for capture verification."""

from __future__ import annotations

from pipetune.gain.gain_models import GainAudit, MixerControl


def _control_by_name(audit: GainAudit, name_fragment: str) -> MixerControl | None:
    fragment = name_fragment.lower()
    for control in audit.mixer_controls:
        if fragment in control.name.lower():
            return control
    return None


def interpret_gain_risks(audit: GainAudit) -> list[str]:
    capture = _control_by_name(audit, "capture")
    mic_boost = _control_by_name(audit, "mic boost") or _control_by_name(audit, "boost")
    digital = _control_by_name(audit, "digital")

    lines: list[str] = []
    if capture and capture.percentages:
        high = max(capture.percentages) >= 80
        low = max(capture.percentages) <= 20
        if high:
            lines.append("Capture gain may be too high.")
        elif low:
            lines.append("Capture gain may be too low.")
        else:
            lines.append("Capture gain is detected; verify with a user-approved capture test.")
    else:
        lines.append("Capture gain state is unknown.")

    if mic_boost and (mic_boost.percentages or mic_boost.db_values):
        if max(mic_boost.percentages or [0]) > 0 or max(mic_boost.db_values or [0.0]) > 0:
            lines.append("Mic boost may contribute to clipping.")
        else:
            lines.append("Mic boost appears disabled or low.")
    else:
        lines.append("Mic boost state is unknown.")

    if digital and (digital.percentages or digital.db_values):
        if max(digital.percentages or [0]) > 0 or max(digital.db_values or [0.0]) > 0:
            lines.append("Digital gain may contribute to clipping.")
        else:
            lines.append("Digital gain appears low.")
    else:
        lines.append("Digital gain state is unknown.")

    return lines


def recommendation_for_status(status: str) -> list[str]:
    if status == "clipping_detected":
        return [
            "Signal clipping was detected.",
            "Lower ALSA Capture, Mic Boost, or Digital gain before lowering only Pulse volume.",
            "If lowering Pulse volume causes silence, the issue may be ALSA-side gain staging or capture source behavior.",
        ]
    if status == "silence_likely":
        return [
            "The capture file contains very weak or near-silent signal.",
            "If a previous test clipped at higher volume, this suggests a gain-stage threshold or wrong capture control, not necessarily a dead microphone.",
            "Raise ALSA Capture gradually before increasing Mic Boost.",
        ]
    if status == "signal_detected":
        return [
            "A usable signal was detected.",
            "This verifies capture route functionality, not calibration-grade quality.",
            "Document current gain state before trying to persist it.",
        ]
    if status == "invalid_file":
        return ["The WAV file could not be analyzed. Provide a valid PCM WAV file."]
    return ["Microphone status remains unknown from this file."]


def render_gain_plan(audit: GainAudit | None = None) -> str:
    known_lines = [
        "Current knowledge:",
        "- Microphone route visibility does not guarantee stable gain staging.",
        "- Clipping at high Pulse/PipeWire volume and silence after lowering it can indicate ALSA-side thresholds or capture source behavior.",
    ]

    if audit is not None:
        known_lines.extend(
            [
                f"- Default source: {audit.default_source or 'unknown'}",
                f"- Default source mute: {_bool_label(audit.default_source_muted)}",
                f"- Pulse/PipeWire volume: {_source_volume_label(audit)}",
                f"- wpctl volume: {_wpctl_volume_label(audit)}",
            ]
        )

    lines = [
        "PipeTune Capture Gain Plan",
        "",
        *known_lines,
        "",
        "Why clipping happens:",
        "- A hot ALSA Capture, Mic Boost, or Digital stage can clip before Pulse/PipeWire volume is lowered.",
        "- Lowering only Pulse/PipeWire volume may not fix clipping that already happened earlier in the capture chain.",
        "",
        "Why silence can happen:",
        "- Some capture paths have thresholds where lowering the wrong stage produces near-zero samples.",
        "- If a previous test clipped, silence after lowering Pulse volume suggests gain-stage threshold or wrong capture control, not necessarily a dead microphone.",
        "",
        "Safe tuning sequence:",
        "- Keep Pulse/PipeWire source volume around a reference level such as 80%.",
        "- Lower ALSA Mic Boost first.",
        "- Lower ALSA Capture if clipping continues.",
        "- Keep Digital gain low initially.",
        "- Test with: pipetune verify mic-capture --duration 5 --confirm-recording --analyze",
        "- If silence occurs, raise ALSA Capture gradually before increasing Mic Boost.",
        "- Use Mic Boost only after Capture alone fails to produce useful signal.",
        "",
        "MANUAL / DO NOT RUN BLINDLY:",
        "pactl set-source-volume @DEFAULT_SOURCE@ 80%",
        "amixer -c 0 set 'Mic Boost' 0%",
        "amixer -c 0 set 'Capture' 60% cap",
        "amixer -c 0 set 'Digital' 0%",
        "",
        "Stop conditions:",
        "- Stop if clipping remains at low boost and moderate capture values.",
        "- Stop if the selected source changes unexpectedly.",
        "- Stop if speaker output, headphones, or other audio routes regress.",
        "",
        "Persistence warning:",
        "- Do not run sudo alsactl store until a stable non-clipping baseline is found.",
        "- If persistence is desired later, document exact stable values first.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)


def render_gain_matrix() -> str:
    rows = [
        "Pulse: 80%, Capture: 50%, Mic Boost: 0%, Digital: 0%",
        "Pulse: 80%, Capture: 60%, Mic Boost: 0%, Digital: 0%",
        "Pulse: 80%, Capture: 70%, Mic Boost: 0%, Digital: 0%",
        "Pulse: 80%, Capture: 80%, Mic Boost: 0%, Digital: 0%",
        "Pulse: 80%, Capture: 70%, Mic Boost: low, Digital: 0%",
    ]
    lines = [
        "PipeTune Capture Gain Test Matrix",
        "",
        "Manual baseline rows:",
        *[f"- {row}" for row in rows],
        "",
        "For each row, run:",
        "pipetune verify mic-capture --duration 5 --confirm-recording --analyze",
        "",
        "Target:",
        "- Peak normalized: 0.200-0.800",
        "- RMS normalized: 0.010-0.150",
        "- Clipping detected: no",
        "- Silence likely: no",
        "- Status: signal_detected",
        "",
        "Safety notes:",
        "- Change only one gain stage at a time.",
        "- Document the exact values for any row that reaches the target.",
        "- Do not store ALSA state until stable values are confirmed.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)


def _bool_label(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _source_volume_label(audit: GainAudit) -> str:
    if audit.pactl_volume and audit.pactl_volume.primary_percent is not None:
        return f"{audit.pactl_volume.primary_percent}%"
    return "unknown"


def _wpctl_volume_label(audit: GainAudit) -> str:
    if audit.wpctl_volume and audit.wpctl_volume.volume is not None:
        return f"{audit.wpctl_volume.volume:.2f}"
    return "unknown"
