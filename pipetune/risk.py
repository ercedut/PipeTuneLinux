"""Risk evaluation and recommendation logic for diagnostics."""

from __future__ import annotations

from collections import Counter

from pipetune.models import RiskFinding


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

RECOMMENDATION_BY_CODE = {
    "pipewire_inactive": "Fix the PipeWire service before attempting audio enhancement.",
    "wireplumber_inactive": "Fix the session manager first. Device routing and profile selection depend on WirePlumber.",
    "no_default_sink": "Default output route could not be detected. Verify the default PipeWire sink using `pactl get-default-sink` and `wpctl status` before attempting enhancement.",
    "no_default_source": "Default input route could not be detected. This affects microphone diagnostics, but playback analysis can continue.",
    "bluetooth_hfp_hsp": "Switch Bluetooth playback to A2DP before judging music/audio quality.",
    "non_pipewire_pulse_server": "pactl indicates a non-PipeWire PulseAudio server. Align the PulseAudio compatibility layer with PipeWire before enhancement work.",
    "route_detection_unavailable": "Route detection commands are unavailable. Install or expose `pactl`/`wpctl` to improve default route diagnostics.",
    "default_sink_unknown": "Default output route is still unknown. Re-check PipeWire route visibility with `pactl` and `wpctl`.",
    "alsa_ucm2_missing": "ALSA UCM2 data is missing while ALSA cards are present. Verify ALSA package completeness for your distribution.",
    "no_playback_devices": "No playback device was detected. Verify hardware visibility and ALSA/PipeWire enumeration.",
    "no_capture_devices": "No capture device was detected. Verify microphone hardware visibility and ALSA/PipeWire enumeration.",
    "easyeffects_missing": "EasyEffects is optional. Install it only if you want manual DSP testing before future PipeTune profile generation.",
    "no_filter_chain": "No PipeWire DSP filter-chain is active. This is normal by default; use 'pipetune profile generate' when you are ready to produce a candidate config file.",
}

HEALTHY_OPTIONAL_RECOMMENDATION = (
    "Core audio routing is healthy. The system is ready for v0.2 profile generation experiments. "
    "Optional tools such as EasyEffects can be installed later for manual DSP testing."
)


def _is_active_service(command_result: dict) -> bool:
    if not command_result:
        return False
    if not command_result.get("available"):
        return False
    if command_result.get("exit_code") != 0:
        return False
    return command_result.get("stdout", "").strip() == "active"


def _highest_severity(findings: list[RiskFinding]) -> str:
    if not findings:
        return "info"
    return min(findings, key=lambda item: SEVERITY_ORDER.get(item.severity, 99)).severity


def evaluate_risks(diagnostic: dict) -> list[RiskFinding]:
    findings: list[RiskFinding] = []

    pipewire_data = diagnostic.get("pipewire", {})
    wireplumber_data = diagnostic.get("wireplumber", {})
    alsa_data = diagnostic.get("alsa", {})
    bluetooth_data = diagnostic.get("bluetooth", {})
    easyeffects_data = diagnostic.get("easyeffects", {})

    pipewire_service = pipewire_data.get("services", {}).get("pipewire", {})
    if not _is_active_service(pipewire_service):
        findings.append(
            RiskFinding(
                severity="critical",
                code="pipewire_inactive",
                message="PipeWire is unavailable or inactive.",
            )
        )

    wireplumber_service = wireplumber_data.get("service_status", {})
    if not _is_active_service(wireplumber_service):
        findings.append(
            RiskFinding(
                severity="critical",
                code="wireplumber_inactive",
                message="WirePlumber is unavailable or inactive.",
            )
        )

    sink_route = pipewire_data.get("default_sink", {"detected": False, "source": "unknown"})
    source_route = pipewire_data.get("default_source", {"detected": False, "source": "unknown"})

    sink_route_commands = [
        pipewire_data.get("pactl_get_default_sink", {}),
        pipewire_data.get("wpctl_inspect_default_sink", {}),
        pipewire_data.get("wpctl_status", {}),
        pipewire_data.get("pactl_info", {}),
    ]
    source_route_commands = [
        pipewire_data.get("pactl_get_default_source", {}),
        pipewire_data.get("wpctl_inspect_default_source", {}),
        pipewire_data.get("wpctl_status", {}),
        pipewire_data.get("pactl_info", {}),
    ]

    sink_commands_available = any(item.get("available") for item in sink_route_commands)
    source_commands_available = any(item.get("available") for item in source_route_commands)

    if not sink_commands_available and not source_commands_available:
        findings.append(
            RiskFinding(
                severity="medium",
                code="route_detection_unavailable",
                message="Default route detection commands are unavailable.",
            )
        )

    playback_devices = alsa_data.get("playback_devices", [])

    if not sink_route.get("detected", False):
        if sink_route.get("explicitly_missing", False) and sink_commands_available:
            findings.append(
                RiskFinding(
                    severity="critical",
                    code="no_default_sink",
                    message="No default output sink detected.",
                )
            )
        elif sink_commands_available and playback_devices:
            findings.append(
                RiskFinding(
                    severity="medium",
                    code="default_sink_unknown",
                    message="Default output route could not be confirmed although playback devices exist.",
                )
            )

    if sink_route.get("detected", False) and not source_route.get("detected", False) and source_commands_available:
        findings.append(
            RiskFinding(
                severity="medium",
                code="no_default_source",
                message="Default input route could not be detected.",
            )
        )

    playback_mode = bluetooth_data.get("playback_mode", "not_active")
    if playback_mode == "hfp_hsp":
        findings.append(
            RiskFinding(
                severity="high",
                code="bluetooth_hfp_hsp",
                message="Bluetooth playback appears to use HFP/HSP/headset mode.",
            )
        )

    pactl_info = pipewire_data.get("pactl_info", {})
    server_name = (pipewire_data.get("pulse_server_name") or "").lower()
    if pactl_info.get("available") and pactl_info.get("exit_code") == 0 and server_name and "pipewire" not in server_name:
        findings.append(
            RiskFinding(
                severity="high",
                code="non_pipewire_pulse_server",
                message="pactl reports a non-PipeWire PulseAudio server.",
            )
        )

    cards = alsa_data.get("cards", [])
    ucm2_exists = alsa_data.get("ucm2_directory", {}).get("exists", False)
    if cards and not ucm2_exists:
        findings.append(
            RiskFinding(
                severity="medium",
                code="alsa_ucm2_missing",
                message="ALSA cards detected but UCM2 directory is missing.",
            )
        )

    if not playback_devices:
        findings.append(
            RiskFinding(
                severity="medium",
                code="no_playback_devices",
                message="No ALSA playback device detected.",
            )
        )

    if not alsa_data.get("capture_devices"):
        findings.append(
            RiskFinding(
                severity="medium",
                code="no_capture_devices",
                message="No ALSA capture device detected.",
            )
        )

    higher_than_low = any(item.severity in {"critical", "high", "medium"} for item in findings)
    if not easyeffects_data.get("installed", False) and not higher_than_low:
        findings.append(
            RiskFinding(
                severity="low",
                code="easyeffects_missing",
                message="EasyEffects is not installed.",
            )
        )

    if not pipewire_data.get("filter_chain_detected", False):
        findings.append(
            RiskFinding(
                severity="low",
                code="no_filter_chain",
                message="No PipeWire filter-chain node is active.",
            )
        )

    if not bluetooth_data.get("bluetooth_audio_active", False):
        findings.append(
            RiskFinding(
                severity="info",
                code="bluetooth_not_active",
                message="Bluetooth audio is not active.",
            )
        )

    if not easyeffects_data.get("installed", False) and not pipewire_data.get("filter_chain_detected", False):
        findings.append(
            RiskFinding(
                severity="info",
                code="no_enhancement_tool_active",
                message="No enhancement tool appears active.",
            )
        )

    findings.append(
        RiskFinding(
            severity="info",
            code="diagnostic_complete",
            message="Diagnostic completed successfully.",
        )
    )

    findings.sort(key=lambda item: SEVERITY_ORDER.get(item.severity, 99))
    return findings


def build_recommendations(diagnostic: dict, findings: list[RiskFinding]) -> list[str]:
    low_codes = {finding.code for finding in findings if finding.severity == "low"}
    has_critical_high_medium = any(finding.severity in {"critical", "high", "medium"} for finding in findings)
    optional_low_codes = {"easyeffects_missing", "no_filter_chain"}

    if not has_critical_high_medium and low_codes and low_codes.issubset(optional_low_codes):
        return [HEALTHY_OPTIONAL_RECOMMENDATION]

    recommendations: list[str] = []

    for finding in findings:
        recommendation = RECOMMENDATION_BY_CODE.get(finding.code)
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)

    if not recommendations:
        severity = _highest_severity(findings)
        if severity in {"low", "info"}:
            recommendations.append("System is ready for v0.2 profile generation experiments.")
        else:
            recommendations.append("Resolve the highest-severity diagnostic finding before attempting enhancement.")

    return recommendations


def summarize_risks(findings: list[RiskFinding]) -> dict[str, int]:
    counter = Counter(finding.severity for finding in findings)
    return dict(counter)


def highest_risk(findings: list[RiskFinding]) -> str:
    return _highest_severity(findings)
