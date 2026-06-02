from __future__ import annotations

from pipetune.gain.gain_parser import (
    parse_amixer_controls,
    parse_pactl_source_mute,
    parse_pactl_source_volume,
    parse_wpctl_volume,
)


def test_pactl_volume_parser_handles_channel_percentages_and_db() -> None:
    output = "Volume: front-left: 52429 / 80% / -5.81 dB, front-right: 52429 / 80% / -5.81 dB"

    volume = parse_pactl_source_volume(output)

    assert volume.percentages == [80, 80]
    assert volume.db_values == [-5.81, -5.81]
    assert volume.channels["front-left"] == 80


def test_pactl_volume_parser_handles_localized_prefix_conservatively() -> None:
    output = "Ses seviyesi: ön-sol: 45875 / 70% / -9,29 dB"

    volume = parse_pactl_source_volume(output)

    assert volume.percentages == [70]
    assert volume.db_values == [-9.29]


def test_pactl_mute_parser_handles_yes_no_and_turkish() -> None:
    assert parse_pactl_source_mute("Mute: yes") is True
    assert parse_pactl_source_mute("Mute: no") is False
    assert parse_pactl_source_mute("Sessiz: evet") is True
    assert parse_pactl_source_mute("Sessiz: hayır") is False
    assert parse_pactl_source_mute("Sessiz: bilinmiyor") is None


def test_wpctl_volume_parser_handles_volume() -> None:
    parsed = parse_wpctl_volume("Volume: 0.80")

    assert parsed.volume == 0.80
    assert parsed.muted is None


def test_wpctl_volume_parser_handles_muted() -> None:
    parsed = parse_wpctl_volume("Volume: 0.40 [MUTED]")

    assert parsed.volume == 0.40
    assert parsed.muted is True


def test_pactl_volume_parser_handles_dot_decimal_db() -> None:
    output = "Volume: front-left: 52397 / 80% / -5.83 dB"

    volume = parse_pactl_source_volume(output)

    assert volume.percentages == [80]
    assert volume.db_values == [-5.83]


def test_pactl_volume_parser_does_not_parse_balance_as_db() -> None:
    output = """
Volume: front-left: 9175 / 14%
        front-right: 9175 / 14%
        balance 0,00
"""

    volume = parse_pactl_source_volume(output)

    assert volume.percentages == [14, 14]
    assert volume.primary_percent == 14
    assert volume.db_values == []


def test_pactl_volume_parser_uses_primary_channel_consistently() -> None:
    output = "Volume: front-left: 32768 / 50% / -18,06 dB, front-right: 39321 / 60% / -13.31 dB"

    volume = parse_pactl_source_volume(output)

    assert volume.primary_percent == 50
    assert volume.db_values == [-18.06, -13.31]


def test_amixer_parser_detects_capture_mic_boost_and_digital() -> None:
    output = """
Simple mixer control 'Capture',0
  Capabilities: cvolume cswitch
  Capture channels: Front Left - Front Right
  Limits: Capture 0 - 63
  Front Left: Capture 42 [67%] [12.00dB] [on]
  Front Right: Capture 42 [67%] [12.00dB] [on]
Simple mixer control 'Mic Boost',0
  Capabilities: volume
  Mono: 0 [0%] [0.00dB]
Simple mixer control 'Digital',0
  Capabilities: cvolume
  Mono: Capture 0 [0%] [0.00dB] [capture]
"""

    controls = parse_amixer_controls(output)
    names = {control.name for control in controls}

    assert "Capture" in names
    assert "Mic Boost" in names
    assert "Digital" in names
    assert next(control for control in controls if control.name == "Digital").capture_enabled is True
