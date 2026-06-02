"""Latest microphone verification status utilities."""

from __future__ import annotations

import json
from pathlib import Path

from pipetune.verify.mic_analyze import DEFAULT_VERIFICATION_DIR, LATEST_VERIFICATION_PATH


def _suggested_next_action(status: str) -> str:
    if status == "clipping_detected":
        return "run pipetune repair gain-plan"
    if status == "silence_likely":
        return "inspect gain controls, then run pipetune repair gain-matrix"
    if status == "signal_detected":
        return "document current gain state before persistence"
    if status == "invalid_file":
        return "analyze a valid local PCM WAV file"
    return "run pipetune verify mic-plan"


def _is_within_directory(path: Path, directory: Path) -> bool:
    try:
        resolved_path = path.resolve(strict=False)
        resolved_dir = directory.resolve(strict=False)
        resolved_path.relative_to(resolved_dir)
        return True
    except ValueError:
        return False


def render_mic_status(latest_path: Path = LATEST_VERIFICATION_PATH) -> str:
    if not latest_path.exists():
        lines = [
            "PipeTune Microphone Verification Status",
            "",
            "State: not_tested",
            "Message: microphone route may be visible, but capture has not been verified",
            "",
            "Privacy note:",
            "- Recording is never automatic.",
            "- Any recording file is local-only and gitignored by default.",
            "",
            "No system configuration was modified.",
        ]
        return "\n".join(lines)

    try:
        payload = json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        lines = [
            "PipeTune Microphone Verification Status",
            "",
            "State: unknown",
            "Message: latest verification file exists but could not be parsed",
            "",
            "No system configuration was modified.",
        ]
        return "\n".join(lines)

    file_path_value = str(payload.get("file_path", "")).strip()
    if not file_path_value:
        lines = [
            "PipeTune Microphone Verification Status",
            "",
            "State: invalid_status",
            "Message: latest verification file is missing the recorded file path",
            "",
            "No system configuration was modified.",
        ]
        return "\n".join(lines)

    if not _is_within_directory(Path(file_path_value), DEFAULT_VERIFICATION_DIR):
        lines = [
            "PipeTune Microphone Verification Status",
            "",
            "State: invalid_status",
            "Latest verification file is outside the local verification directory. Ignoring stale or unsafe status.",
            "Message: microphone route may be visible, but capture has not been verified",
            "",
            "Privacy note:",
            "- Recording is never automatic.",
            "- Any recording file is local-only and gitignored by default.",
            "",
            "No system configuration was modified.",
        ]
        return "\n".join(lines)

    status = str(payload.get("status", "unknown"))
    lines = [
        "PipeTune Microphone Verification Status",
        "",
        f"Latest file: {file_path_value}",
        f"Status: {status}",
        f"Duration: {float(payload.get('duration_seconds', 0.0)):.2f} s",
        f"RMS normalized: {float(payload.get('rms_normalized', 0.0)):.3f}",
        f"Peak normalized: {float(payload.get('peak_normalized', 0.0)):.3f}",
        f"Clipping detected: {'yes' if payload.get('clipping_detected') else 'no'}",
        f"Silence likely: {'yes' if payload.get('silence_likely') else 'no'}",
        f"Suggested next action: {_suggested_next_action(status)}",
        "",
        "Privacy note:",
        "- Review recordings before sharing.",
        "- Share summarized analysis instead of raw WAV files when possible.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
