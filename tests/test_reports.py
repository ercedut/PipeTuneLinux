from __future__ import annotations

import json

from pipetune.reports.json_report import build_json_report
from pipetune.reports.markdown_report import build_markdown_report


def _sample_diagnostic() -> dict:
    return {
        "metadata": {
            "generated_at": "2026-05-30T00:00:00+00:00",
            "tool_version": "0.1.0",
            "hostname": "host",
            "platform": "Linux",
            "python_version": "3.11.0",
        },
        "pipewire": {
            "services": {
                "pipewire": {"available": True, "exit_code": 0, "stdout": "active\n", "timed_out": False},
                "pipewire_pulse": {"available": True, "exit_code": 0, "stdout": "active\n", "timed_out": False},
            },
            "pactl_get_default_sink": {"available": True},
            "pactl_get_default_source": {"available": True},
            "wpctl_inspect_default_sink": {"available": True},
            "wpctl_inspect_default_source": {"available": True},
            "pactl_info": {"available": True},
            "wpctl_status": {"available": True},
            "pw_dump": {"available": True},
            "default_sink": {
                "detected": True,
                "name": "alsa_output.pci-0000_00_1f.3.analog-stereo",
                "source": "pactl_get_default_sink",
            },
            "default_source": {
                "detected": True,
                "name": "alsa_input.pci-0000_00_1f.3.analog-stereo",
                "source": "pactl_get_default_source",
            },
            "filter_chain_detected": False,
        },
        "wireplumber": {
            "service_status": {"available": True, "exit_code": 0, "stdout": "active\n", "timed_out": False},
            "has_managed_audio_nodes": True,
        },
        "alsa": {
            "cards": ["card0"],
            "playback_devices": ["playback"],
            "capture_devices": ["capture"],
            "ucm2_directory": {"exists": True},
        },
        "bluetooth": {
            "bluetooth_audio_active": False,
            "bluetooth_card_names": [],
            "active_profiles": [],
            "playback_mode": "not_active",
        },
        "easyeffects": {"installed": False},
        "risks": [{"severity": "low", "code": "easyeffects_missing", "message": "EasyEffects is not installed."}],
        "recommendations": ["EasyEffects is optional. Install it only if you want manual DSP testing before future PipeTune profile generation."],
        "raw_command_status": [
            {
                "component": "pipewire",
                "name": "pipewire",
                "command": "systemctl --user is-active pipewire",
                "available": True,
                "exit_code": 0,
                "timed_out": False,
                "error": None,
            }
        ],
    }


def test_markdown_report_contains_required_sections() -> None:
    report = build_markdown_report(_sample_diagnostic())

    required_sections = [
        "# PipeTune Linux Audio Diagnostic Report",
        "## Executive Summary",
        "Highest Risk",
        "Primary Recommendation",
        "## PipeWire Status",
        "## WirePlumber Status",
        "## ALSA Devices",
        "## Default Audio Routes",
        "## Bluetooth Audio",
        "## Enhancement Tools",
        "## Risk Findings",
        "## Recommended Next Steps",
        "## Raw Command Availability Summary",
    ]

    for section in required_sections:
        assert section in report


def test_json_report_contains_required_top_level_keys_and_default_routes() -> None:
    report_json = build_json_report(_sample_diagnostic())
    payload = json.loads(report_json)

    expected_keys = {
        "metadata",
        "pipewire",
        "wireplumber",
        "alsa",
        "bluetooth",
        "easyeffects",
        "risks",
        "recommendations",
        "raw_command_status",
    }

    assert expected_keys.issubset(payload.keys())
    assert set(payload["pipewire"]["default_sink"].keys()) >= {"detected", "name", "source"}
    assert set(payload["pipewire"]["default_source"].keys()) >= {"detected", "name", "source"}
