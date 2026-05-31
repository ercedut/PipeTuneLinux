"""Manual microphone verification planning."""

from __future__ import annotations


def render_mic_test_plan() -> str:
    lines = [
        "PipeTune Microphone Test Plan",
        "",
        "Route visibility warning:",
        "- Route visible does not mean microphone works.",
        "- Capture test must be explicit and user-approved.",
        "- Built-in mic should not be used for calibration until verified.",
        "- External USB microphone is recommended for calibration workflows.",
        "",
        "Read-only inspection commands (manual):",
        "- pactl get-default-source",
        "- pactl list sources short",
        "- arecord -l",
        "- arecord -L",
        "",
        "Optional recording verification commands:",
        "MANUAL / CREATES LOCAL AUDIO FILE / RUN ONLY IF YOU APPROVE RECORDING",
        "- arecord -d 5 -f cd test-mic.wav",
        "- aplay test-mic.wav",
        "",
        "Safety notes:",
        "- Do not treat recording success as calibration-grade quality proof.",
        "- Do not use built-in microphone for measurement workflows until validated across repeated tests.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
