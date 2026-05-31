"""Read-only microphone route audit."""

from __future__ import annotations

import re

from pipetune.collectors.command import run_command
from pipetune.hardware.models import MicAuditResult

_INTERNAL_MIC_HINTS = [
    "analog-input-internal-mic",
    "internal microphone",
    "built-in audio analog stereo",
    "alsa_input",
]


def _extract_capture_device_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if "card " in line.lower())


def _extract_source_count_from_short(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if line.strip() and not line.lower().startswith("source"):
            count += 1
    return count


def _extract_default_source_from_pactl_info(text: str) -> str | None:
    for line in text.splitlines():
        if line.lower().startswith("default source:"):
            value = line.split(":", 1)[1].strip()
            return value or None
    return None


def _extract_default_source_state(source_text: str, default_source: str | None) -> tuple[bool | None, str | None]:
    if not source_text.strip():
        return None, None

    if default_source:
        blocks = re.split(r"\n(?=Source #)", source_text)
        for block in blocks:
            if f"Name: {default_source}" not in block:
                continue
            muted = None
            state = None
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("mute:"):
                    muted = stripped.split(":", 1)[1].strip().lower() == "yes"
                elif stripped.lower().startswith("state:"):
                    state = stripped.split(":", 1)[1].strip()
            return muted, state

    lowered = source_text.lower()
    muted = None
    if "mute: yes" in lowered:
        muted = True
    elif "mute: no" in lowered:
        muted = False

    state = None
    if "state: suspended" in lowered:
        state = "SUSPENDED"
    elif "state: running" in lowered:
        state = "RUNNING"
    elif "state: idle" in lowered:
        state = "IDLE"

    return muted, state


def _internal_mic_visibility(default_source: str | None, all_source_text: str) -> str:
    corpus = "\n".join(filter(None, [default_source or "", all_source_text])).lower()

    if any(hint in corpus for hint in _INTERNAL_MIC_HINTS):
        return "yes"
    if corpus.strip():
        return "no"
    return "unknown"


def collect_mic_audit() -> MicAuditResult:
    arecord_list = run_command(["arecord", "-l"])
    arecord_long = run_command(["arecord", "-L"])
    pactl_sources = run_command(["pactl", "list", "sources"])
    pactl_sources_short = run_command(["pactl", "list", "sources", "short"])
    wpctl_status = run_command(["wpctl", "status"])
    pactl_default_source = run_command(["pactl", "get-default-source"])
    pactl_info = run_command(["pactl", "info"])

    capture_count = 0
    if arecord_list.available and arecord_list.exit_code == 0:
        capture_count = _extract_capture_device_count(arecord_list.stdout)

    source_count: int | None = None
    if pactl_sources_short.available and pactl_sources_short.exit_code == 0:
        source_count = _extract_source_count_from_short(pactl_sources_short.stdout)

    default_source: str | None = None
    if pactl_default_source.available and pactl_default_source.exit_code == 0:
        for line in pactl_default_source.stdout.splitlines():
            candidate = line.strip()
            if candidate:
                default_source = candidate
                break

    if not default_source and pactl_info.available and pactl_info.exit_code == 0:
        default_source = _extract_default_source_from_pactl_info(pactl_info.stdout)

    muted, state = _extract_default_source_state(
        pactl_sources.stdout if pactl_sources.available and pactl_sources.exit_code == 0 else "",
        default_source,
    )

    internal_mic_route_visible = _internal_mic_visibility(
        default_source,
        pactl_sources.stdout if pactl_sources.available and pactl_sources.exit_code == 0 else "",
    )

    if capture_count > 0 or (source_count is not None and source_count > 0):
        microphone_status = "visible"
    elif source_count == 0 or (not arecord_list.available and not pactl_sources_short.available):
        microphone_status = "unavailable"
    else:
        microphone_status = "unknown"

    warnings: list[str] = []
    if default_source and (muted is True or (state or "").upper() in {"SUSPENDED", "UNAVAILABLE"}):
        warnings.append("Default source exists but capture route may be unreliable (muted/suspended/unavailable).")
    elif default_source:
        warnings.append("Default source exists. Capture route visible, but microphone function is not confirmed without capture test.")
    else:
        warnings.append("Default source could not be confirmed. Capture route may be unreliable.")

    if not arecord_long.available or arecord_long.exit_code not in {0, 1}:
        warnings.append("Extended ALSA capture device listing is unavailable.")
    if not wpctl_status.available:
        warnings.append("wpctl status is unavailable; route visibility may be incomplete.")

    return MicAuditResult(
        alsa_capture_devices_count=capture_count,
        source_count=source_count,
        default_source=default_source,
        default_source_muted=muted,
        default_source_state=state,
        internal_mic_route_visible=internal_mic_route_visible,
        capture_test_performed=False,
        microphone_status=microphone_status,
        safety_recommendation="Capture route visible does not prove microphone functionality. Run a manual user-approved capture test outside PipeTune if needed.",
        warnings=warnings,
    )


def render_mic_audit_summary(result: MicAuditResult) -> str:
    if result.default_source_muted is None and result.default_source_state is None:
        source_flags = "unknown"
    else:
        source_flags = f"muted={result.default_source_muted}, state={result.default_source_state or 'unknown'}"

    lines = [
        "PipeTune Microphone Audit",
        f"- ALSA capture devices: {result.alsa_capture_devices_count}",
        f"- PipeWire/Pulse sources: {result.source_count if result.source_count is not None else 'unknown'}",
        f"- Default source: {result.default_source or 'unknown'}",
        f"- Default source route flags: {source_flags}",
        f"- Internal mic route visible: {result.internal_mic_route_visible}",
        f"- Capture test performed: {'yes' if result.capture_test_performed else 'no'}",
        f"- Microphone status: {result.microphone_status}",
        f"- Safety recommendation: {result.safety_recommendation}",
    ]

    if result.warnings:
        lines.append("- Warnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
