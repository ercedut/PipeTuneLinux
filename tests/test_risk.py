from __future__ import annotations

from pipetune.risk import HEALTHY_OPTIONAL_RECOMMENDATION, build_recommendations, evaluate_risks


def _command_result(available: bool = True, exit_code: int = 0, stdout: str = "", stderr: str = "") -> dict:
    return {
        "available": available,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": False,
        "error": None,
    }


def _base_diagnostic() -> dict:
    return {
        "pipewire": {
            "services": {
                "pipewire": _command_result(stdout="active\n"),
                "pipewire_pulse": _command_result(stdout="active\n"),
            },
            "pactl_get_default_sink": _command_result(stdout="alsa_output.pci-0000_00_1f.3.analog-stereo\n"),
            "pactl_get_default_source": _command_result(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
            "wpctl_inspect_default_sink": _command_result(),
            "wpctl_inspect_default_source": _command_result(),
            "pactl_info": _command_result(),
            "wpctl_status": _command_result(),
            "default_sink": {
                "detected": True,
                "name": "alsa_output.pci-0000_00_1f.3.analog-stereo",
                "source": "pactl_get_default_sink",
                "explicitly_missing": False,
            },
            "default_source": {
                "detected": True,
                "name": "alsa_input.pci-0000_00_1f.3.analog-stereo",
                "source": "pactl_get_default_source",
                "explicitly_missing": False,
            },
            "filter_chain_detected": False,
            "pulse_server_name": "PulseAudio (on PipeWire 1.0.0)",
        },
        "wireplumber": {
            "service_status": _command_result(stdout="active\n")
        },
        "alsa": {
            "cards": ["0 [PCH]"],
            "ucm2_directory": {"exists": True},
            "playback_devices": ["card 0: PCH"],
            "capture_devices": ["card 0: PCH"],
        },
        "bluetooth": {
            "playback_mode": "not_active",
            "bluetooth_audio_active": False,
        },
        "easyeffects": {"installed": False},
    }


def _has_code(findings: list, code: str, severity: str | None = None) -> bool:
    for finding in findings:
        if finding.code == code and (severity is None or finding.severity == severity):
            return True
    return False


def test_pipewire_inactive_creates_critical_risk() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["pipewire"]["services"]["pipewire"] = _command_result(exit_code=3, stdout="inactive\n")

    findings = evaluate_risks(diagnostic)
    assert _has_code(findings, "pipewire_inactive", "critical")


def test_wireplumber_inactive_creates_critical_risk() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["wireplumber"]["service_status"] = _command_result(exit_code=3, stdout="inactive\n")

    findings = evaluate_risks(diagnostic)
    assert _has_code(findings, "wireplumber_inactive", "critical")


def test_bluetooth_hfp_hsp_creates_high_risk() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["bluetooth"]["playback_mode"] = "hfp_hsp"
    diagnostic["bluetooth"]["bluetooth_audio_active"] = True

    findings = evaluate_risks(diagnostic)
    assert _has_code(findings, "bluetooth_hfp_hsp", "high")


def test_default_sink_detected_avoids_no_default_sink_critical() -> None:
    diagnostic = _base_diagnostic()

    findings = evaluate_risks(diagnostic)
    assert not _has_code(findings, "no_default_sink", "critical")


def test_route_detection_unavailable_is_medium_not_critical() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["pipewire"]["pactl_get_default_sink"] = _command_result(available=False)
    diagnostic["pipewire"]["pactl_get_default_source"] = _command_result(available=False)
    diagnostic["pipewire"]["wpctl_inspect_default_sink"] = _command_result(available=False)
    diagnostic["pipewire"]["wpctl_inspect_default_source"] = _command_result(available=False)
    diagnostic["pipewire"]["wpctl_status"] = _command_result(available=False)
    diagnostic["pipewire"]["pactl_info"] = _command_result(available=False)
    diagnostic["pipewire"]["default_sink"] = {
        "detected": False,
        "name": None,
        "source": "unknown",
        "explicitly_missing": False,
    }
    diagnostic["pipewire"]["default_source"] = {
        "detected": False,
        "name": None,
        "source": "unknown",
        "explicitly_missing": False,
    }

    findings = evaluate_risks(diagnostic)
    assert _has_code(findings, "route_detection_unavailable", "medium")
    assert not _has_code(findings, "no_default_sink", "critical")


def test_critical_recommendation_overrides_easyeffects_missing() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["pipewire"]["services"]["pipewire"] = _command_result(exit_code=3, stdout="inactive\n")

    findings = evaluate_risks(diagnostic)
    recommendations = build_recommendations(diagnostic, findings)

    assert recommendations
    assert recommendations[0] == "Fix the PipeWire service before attempting audio enhancement."


def test_easyeffects_missing_low_only_without_higher_severity() -> None:
    healthy = _base_diagnostic()
    healthy_findings = evaluate_risks(healthy)
    assert _has_code(healthy_findings, "easyeffects_missing", "low")

    degraded = _base_diagnostic()
    degraded["pipewire"]["default_source"] = {
        "detected": False,
        "name": None,
        "source": "unknown",
        "explicitly_missing": False,
    }
    degraded_findings = evaluate_risks(degraded)
    assert _has_code(degraded_findings, "no_default_source", "medium")
    assert not _has_code(degraded_findings, "easyeffects_missing", "low")


def test_healthy_optional_only_uses_profile_generation_readiness_recommendation() -> None:
    diagnostic = _base_diagnostic()
    findings = evaluate_risks(diagnostic)

    recommendations = build_recommendations(diagnostic, findings)

    assert recommendations
    assert recommendations[0] == HEALTHY_OPTIONAL_RECOMMENDATION


def test_higher_severity_prevents_healthy_optional_recommendation() -> None:
    diagnostic = _base_diagnostic()
    diagnostic["pipewire"]["default_source"] = {
        "detected": False,
        "name": None,
        "source": "unknown",
        "explicitly_missing": False,
    }
    findings = evaluate_risks(diagnostic)

    recommendations = build_recommendations(diagnostic, findings)

    assert recommendations
    assert recommendations[0] != HEALTHY_OPTIONAL_RECOMMENDATION
