"""Privacy-safe microphone verification guidance."""

from __future__ import annotations


def render_mic_verification_plan() -> str:
    lines = [
        "PipeTune Microphone Verification Plan",
        "",
        "Why:",
        "- A visible default source does not prove the microphone captures sound.",
        "- A short explicit capture test is required.",
        "",
        "Privacy:",
        "- PipeTune never records unless `--confirm-recording` is passed.",
        "- Generated WAV files stay local.",
        "- Generated WAV/JSON files are gitignored.",
        "",
        "Recommended flow:",
        "1. Run `pipetune hardware mic-audit`",
        "2. Run `pipetune verify mic-capture --duration 5 --confirm-recording --analyze`",
        "3. Speak clearly during the 5-second recording.",
        "4. Review the analysis.",
        "5. Do not share raw WAV files publicly.",
        "",
        "Safety notes:",
        "- Built-in mic must not be used for calibration unless verified.",
        "- PipeTune does not upload recordings.",
        "",
        "No system configuration was modified.",
    ]
    return "\n".join(lines)
