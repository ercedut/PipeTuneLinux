"""ALSA collector."""

from __future__ import annotations

from pathlib import Path

from pipetune.collectors.command import run_command


PROC_ASOUND_CARDS = Path("/proc/asound/cards")
PROC_ASOUND_VERSION = Path("/proc/asound/version")
ALSA_UCM2_DIR = Path("/usr/share/alsa/ucm2")


def _read_file(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False, "content": None, "error": None}
    try:
        return {"path": str(path), "exists": True, "content": path.read_text(encoding="utf-8", errors="replace"), "error": None}
    except OSError as exc:
        return {"path": str(path), "exists": True, "content": None, "error": str(exc)}


def _extract_device_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if "card " in line.lower():
            lines.append(line.strip())
    return lines


def _extract_card_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0].isdigit() and "[" in stripped:
            lines.append(stripped)
    return lines


def collect_alsa_data() -> dict:
    aplay_list = run_command(["aplay", "-l"])
    arecord_list = run_command(["arecord", "-l"])
    cards_file = _read_file(PROC_ASOUND_CARDS)
    version_file = _read_file(PROC_ASOUND_VERSION)

    playback_devices: list[str] = []
    capture_devices: list[str] = []
    cards: list[str] = []

    if aplay_list.available and aplay_list.exit_code == 0:
        playback_devices = _extract_device_lines(aplay_list.stdout)
    if arecord_list.available and arecord_list.exit_code == 0:
        capture_devices = _extract_device_lines(arecord_list.stdout)
    if cards_file["exists"] and cards_file["content"]:
        cards = _extract_card_lines(cards_file["content"])

    return {
        "aplay_list": aplay_list.to_dict(),
        "arecord_list": arecord_list.to_dict(),
        "cards_file": cards_file,
        "version_file": version_file,
        "ucm2_directory": {
            "path": str(ALSA_UCM2_DIR),
            "exists": ALSA_UCM2_DIR.exists(),
        },
        "playback_devices": playback_devices,
        "capture_devices": capture_devices,
        "cards": cards,
    }
