"""Markdown report generator."""

from __future__ import annotations

from pipetune.models import RiskFinding
from pipetune.risk import highest_risk


def _service_line(command_result: dict) -> str:
    if not command_result.get("available"):
        return "unavailable"
    if command_result.get("timed_out"):
        return "timed out"
    if command_result.get("exit_code") == 0:
        return command_result.get("stdout", "").strip() or "active"
    return command_result.get("stdout", "").strip() or "inactive"


def _route_source_label(source: str) -> str:
    mapping = {
        "pactl_get_default_sink": "pactl",
        "pactl_get_default_source": "pactl",
        "wpctl_inspect": "wpctl inspect",
        "wpctl_status": "wpctl status",
        "pactl_info": "pactl info",
        "unknown": "route detection incomplete",
    }
    return mapping.get(source, source)


def _route_line(route: dict) -> str:
    if route.get("detected") and route.get("name"):
        return f"{route['name']} (from {_route_source_label(route.get('source', 'unknown'))})"
    return "unknown (route detection incomplete)"


def build_markdown_report(diagnostic: dict) -> str:
    metadata = diagnostic["metadata"]
    pipewire = diagnostic["pipewire"]
    wireplumber = diagnostic["wireplumber"]
    alsa = diagnostic["alsa"]
    bluetooth = diagnostic["bluetooth"]
    easyeffects = diagnostic["easyeffects"]
    findings = [RiskFinding(**item) for item in diagnostic["risks"]]
    highest = highest_risk(findings)
    primary_recommendation = diagnostic["recommendations"][0] if diagnostic["recommendations"] else "none"

    lines: list[str] = [
        "# PipeTune Linux Audio Diagnostic Report",
        "",
        f"- generated_at: {metadata['generated_at']}",
        f"- tool_version: {metadata['tool_version']}",
        f"- hostname: {metadata['hostname']}",
        f"- platform: {metadata['platform']}",
        f"- python_version: {metadata['python_version']}",
        "",
        "## Executive Summary",
        f"- Total findings: {len(diagnostic['risks'])}",
        f"- Highest Risk: {highest}",
        f"- Primary Recommendation: {primary_recommendation}",
        "",
        "## PipeWire Status",
        f"- pipewire: {_service_line(pipewire['services']['pipewire'])}",
        f"- pipewire-pulse: {_service_line(pipewire['services']['pipewire_pulse'])}",
        f"- pactl info available: {'yes' if pipewire['pactl_info']['available'] else 'no'}",
        f"- wpctl status available: {'yes' if pipewire['wpctl_status']['available'] else 'no'}",
        f"- pw-dump available: {'yes' if pipewire['pw_dump']['available'] else 'no'}",
        f"- filter-chain detected: {'yes' if pipewire['filter_chain_detected'] else 'no'}",
        "",
        "## WirePlumber Status",
        f"- wireplumber: {_service_line(wireplumber['service_status'])}",
        f"- managed audio nodes visible: {'yes' if wireplumber['has_managed_audio_nodes'] else 'no'}",
        "",
        "## ALSA Devices",
        f"- cards detected: {len(alsa['cards'])}",
        f"- playback devices detected: {len(alsa['playback_devices'])}",
        f"- capture devices detected: {len(alsa['capture_devices'])}",
        f"- ucm2 present: {'yes' if alsa['ucm2_directory']['exists'] else 'no'}",
        "",
        "## Default Audio Routes",
        f"- default sink: {_route_line(pipewire.get('default_sink', {}))}",
        f"- default source: {_route_line(pipewire.get('default_source', {}))}",
        "",
        "## Bluetooth Audio",
        f"- bluetooth audio active: {'yes' if bluetooth['bluetooth_audio_active'] else 'no'}",
        f"- bluetooth cards: {', '.join(bluetooth['bluetooth_card_names']) if bluetooth['bluetooth_card_names'] else 'none'}",
        f"- playback mode hint: {bluetooth.get('playback_mode', 'unknown')}",
        f"- active profiles: {', '.join(bluetooth['active_profiles']) if bluetooth['active_profiles'] else 'none'}",
        "",
        "## Enhancement Tools",
        f"- EasyEffects installed: {'yes' if easyeffects['installed'] else 'no'}",
        f"- PipeWire filter-chain active: {'yes' if pipewire['filter_chain_detected'] else 'no'}",
        "",
        "## Risk Findings",
    ]

    for item in diagnostic["risks"]:
        lines.append(f"- [{item['severity']}] {item['code']}: {item['message']}")

    lines.extend(["", "## Recommended Next Steps"])
    for recommendation in diagnostic["recommendations"]:
        lines.append(f"- {recommendation}")

    lines.extend(["", "## Raw Command Availability Summary"])
    for entry in diagnostic["raw_command_status"]:
        lines.append(
            "- "
            f"{entry['component']}.{entry['name']} | command={entry['command']} | "
            f"available={entry['available']} | exit_code={entry['exit_code']} | "
            f"timed_out={entry['timed_out']} | error={entry['error']}"
        )

    lines.append("")
    return "\n".join(lines)
