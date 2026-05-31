"""Manual guided checklist for HDA troubleshooting."""

from __future__ import annotations


def render_repair_checklist() -> str:
    lines = [
        "PipeTune Guided Repair Checklist",
        "",
        "Manual checklist:",
        "1. Confirm current speaker output works before any manual change.",
        "2. Plug headphone and observe output switch behavior.",
        "3. Confirm default sink/source before jack insertion.",
        "4. Confirm default sink/source after jack insertion and removal.",
        "5. Check if microphone input meter moves in pavucontrol.",
        "6. Perform optional manual mic capture test only if explicitly approved.",
        "7. Document every change and observed behavior with timestamps.",
        "",
        "Stop conditions:",
        "- Stop if speaker output regresses.",
        "- Stop if headphone routing becomes worse.",
        "- Stop if microphone route disappears.",
        "- Stop if behavior becomes non-deterministic.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
