"""Device listing command."""

from __future__ import annotations

from pipetune.collectors.command import run_command


def _parse_wpctl_devices(text: str) -> list[str]:
    devices: list[str] = []
    section = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped in {"Sinks:", "Sources:"}:
            section = stripped[:-1].lower()
            continue
        if section in {"sinks", "sources"} and stripped:
            if stripped.endswith(":"):
                section = None
                continue
            if stripped.startswith("├") or stripped.startswith("└") or stripped[0].isdigit() or stripped.startswith("*"):
                devices.append(f"{section}: {stripped}")
    return devices


def _parse_pactl_items(text: str) -> list[str]:
    items: list[str] = []
    current_name = None
    current_desc = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Name:"):
            if current_name or current_desc:
                items.append(f"name={current_name or 'unknown'} desc={current_desc or 'n/a'}")
            current_name = line.split(":", 1)[1].strip()
            current_desc = None
        elif line.startswith("Description:"):
            current_desc = line.split(":", 1)[1].strip()

    if current_name or current_desc:
        items.append(f"name={current_name or 'unknown'} desc={current_desc or 'n/a'}")

    return items


def _parse_alsa_cards(text: str) -> list[str]:
    cards: list[str] = []
    for line in text.splitlines():
        if "card " in line.lower():
            cards.append(line.strip())
    return cards


def collect_devices() -> dict:
    wpctl_status = run_command(["wpctl", "status"])
    pactl_sinks = run_command(["pactl", "list", "sinks"])
    pactl_sources = run_command(["pactl", "list", "sources"])
    aplay_list = run_command(["aplay", "-l"])
    arecord_list = run_command(["arecord", "-l"])

    wpctl_devices = []
    if wpctl_status.available and wpctl_status.exit_code == 0:
        wpctl_devices = _parse_wpctl_devices(wpctl_status.stdout)

    sink_items = []
    if pactl_sinks.available and pactl_sinks.exit_code == 0:
        sink_items = _parse_pactl_items(pactl_sinks.stdout)

    source_items = []
    if pactl_sources.available and pactl_sources.exit_code == 0:
        source_items = _parse_pactl_items(pactl_sources.stdout)

    alsa_playback = []
    if aplay_list.available and aplay_list.exit_code == 0:
        alsa_playback = _parse_alsa_cards(aplay_list.stdout)

    alsa_capture = []
    if arecord_list.available and arecord_list.exit_code == 0:
        alsa_capture = _parse_alsa_cards(arecord_list.stdout)

    return {
        "wpctl": wpctl_status.to_dict(),
        "pactl_sinks": pactl_sinks.to_dict(),
        "pactl_sources": pactl_sources.to_dict(),
        "aplay": aplay_list.to_dict(),
        "arecord": arecord_list.to_dict(),
        "wpctl_devices": wpctl_devices,
        "pactl_sink_devices": sink_items,
        "pactl_source_devices": source_items,
        "alsa_playback_devices": alsa_playback,
        "alsa_capture_devices": alsa_capture,
    }


def render_devices_output(devices_data: dict) -> str:
    lines = ["Detected audio devices"]

    lines.append("- From wpctl status:")
    lines.extend([f"  - {item}" for item in devices_data.get("wpctl_devices", [])] or ["  - none detected"])

    lines.append("- From pactl sinks:")
    lines.extend([f"  - {item}" for item in devices_data.get("pactl_sink_devices", [])] or ["  - none detected"])

    lines.append("- From pactl sources:")
    lines.extend([f"  - {item}" for item in devices_data.get("pactl_source_devices", [])] or ["  - none detected"])

    lines.append("- From aplay -l:")
    lines.extend([f"  - {item}" for item in devices_data.get("alsa_playback_devices", [])] or ["  - none detected"])

    lines.append("- From arecord -l:")
    lines.extend([f"  - {item}" for item in devices_data.get("alsa_capture_devices", [])] or ["  - none detected"])

    return "\n".join(lines)
