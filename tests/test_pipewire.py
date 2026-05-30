from __future__ import annotations

from pipetune.collectors.pipewire import parse_pactl_default_name


def test_parse_pactl_get_default_sink_output() -> None:
    output = "alsa_output.pci-0000_00_1f.3.analog-stereo\n"
    assert parse_pactl_default_name(output) == "alsa_output.pci-0000_00_1f.3.analog-stereo"


def test_parse_pactl_get_default_source_output() -> None:
    output = "alsa_input.pci-0000_00_1f.3.analog-stereo\n"
    assert parse_pactl_default_name(output) == "alsa_input.pci-0000_00_1f.3.analog-stereo"
