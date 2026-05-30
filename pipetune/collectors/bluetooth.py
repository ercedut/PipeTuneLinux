"""Bluetooth audio collector."""

from __future__ import annotations

from pipetune.collectors.command import run_command


HFP_WORDS = ("hfp", "hsp", "headset", "handsfree")
A2DP_WORDS = ("a2dp",)


def _extract_bluez_cards(text: str) -> list[str]:
    cards: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Name:") and "bluez_card" in stripped:
            cards.append(stripped.split("Name:", 1)[1].strip())
    return cards


def _extract_active_profiles(text: str) -> list[str]:
    profiles: list[str] = []
    current_card_is_bluez = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Card #"):
            current_card_is_bluez = False
        elif line.startswith("Name:") and "bluez_card" in line:
            current_card_is_bluez = True
        elif current_card_is_bluez and line.lower().startswith("active profile:"):
            profiles.append(line.split(":", 1)[1].strip())

    return profiles


def collect_bluetooth_data() -> dict:
    pactl_cards = run_command(["pactl", "list", "cards"])

    bluez_cards: list[str] = []
    active_profiles: list[str] = []
    mode = "not_active"

    if pactl_cards.available and pactl_cards.exit_code == 0:
        bluez_cards = _extract_bluez_cards(pactl_cards.stdout)
        active_profiles = _extract_active_profiles(pactl_cards.stdout)

    lower_profiles = " ".join(active_profiles).lower()
    if bluez_cards:
        if any(word in lower_profiles for word in HFP_WORDS):
            mode = "hfp_hsp"
        elif any(word in lower_profiles for word in A2DP_WORDS):
            mode = "a2dp"
        else:
            mode = "unknown"

    profile_hints: list[str] = []
    source_text = lower_profiles if active_profiles else pactl_cards.stdout.lower()
    for word in (*HFP_WORDS, *A2DP_WORDS):
        if word in source_text and word not in profile_hints:
            profile_hints.append(word)

    return {
        "pactl_cards": pactl_cards.to_dict(),
        "bluetooth_cards_detected": bool(bluez_cards),
        "bluetooth_card_names": bluez_cards,
        "active_profiles": active_profiles,
        "profile_hints": profile_hints,
        "playback_mode": mode,
        "bluetooth_audio_active": bool(bluez_cards),
    }
