"""Hardware quirk status for profile activation preflight."""

from __future__ import annotations

import json
from pathlib import Path

from pipetune.hardware.hda_audit import collect_hda_audit
from pipetune.safety.models import HardwareQuirkMetadata
from pipetune.verify.mic_analyze import LATEST_VERIFICATION_PATH


def collect_hardware_quirk_metadata(latest_mic_status_path: Path = LATEST_VERIFICATION_PATH) -> HardwareQuirkMetadata:
    hda = collect_hda_audit()
    evidence: list[str] = []
    warnings: list[str] = []

    quirk_detected = bool(hda.manual_hda_retask_detected or hda.manual_hda_retask_suspected)
    if hda.manual_hda_retask_detected:
        quirk_type = "manual_hda_pin_retask"
        evidence.append("HDA retask indicators detected.")
    elif hda.manual_hda_retask_suspected:
        quirk_type = "unknown_hda_routing"
        evidence.append("HDA routing issue suspected from read-only audit.")
    else:
        quirk_type = "none"
        evidence.append("No HDA retask indicator detected.")

    if hda.codec_files:
        evidence.append("HDA codec files found.")
    if hda.retask_reference_hits:
        evidence.append("hda-jack-retask references detected.")
    if hda.warnings:
        warnings.extend(hda.warnings)

    mic_reliable = _read_builtin_mic_reliability(latest_mic_status_path, evidence)
    if mic_reliable is False:
        warnings.append("Microphone verification indicates silence or clipping instability.")

    if quirk_detected:
        warnings.append("Do not auto-apply speaker/headphone profiles without manual confirmation.")

    return HardwareQuirkMetadata(
        quirk_detected=quirk_detected,
        quirk_type=quirk_type,
        auto_switch_safe=not quirk_detected,
        built_in_microphone_reliable=mic_reliable,
        requires_manual_output_confirmation=quirk_detected,
        evidence=evidence,
        warnings=warnings,
    )


def render_hardware_quirk_status(metadata: HardwareQuirkMetadata) -> str:
    lines = [
        "PipeTune Hardware Quirk Status",
        "",
        f"Hardware quirk detected: {'yes' if metadata.quirk_detected else 'no'}",
        f"Quirk type: {metadata.quirk_type or 'unknown'}",
        f"Auto-switch safe: {'yes' if metadata.auto_switch_safe else 'no'}",
        f"Built-in microphone reliable: {_optional_bool(metadata.built_in_microphone_reliable)}",
        f"Manual output confirmation required: {'yes' if metadata.requires_manual_output_confirmation else 'no'}",
        "",
        "Evidence:",
    ]
    lines.extend(f"* {item}" for item in metadata.evidence)
    if metadata.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"* {warning}" for warning in metadata.warnings)
    lines.extend(["", "No system configuration was modified."])
    return "\n".join(lines)


def _read_builtin_mic_reliability(path: Path, evidence: list[str]) -> bool | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    status = str(payload.get("status", "unknown"))
    evidence.append(f"Latest microphone verification status: {status}.")
    if status == "signal_detected":
        return True
    if status in {"silence_likely", "clipping_detected"}:
        return False
    return None


def _optional_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
