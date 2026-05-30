"""Diagnostic orchestration for PipeTune Linux."""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import socket

from pipetune import CODENAME, __version__
from pipetune.collectors.alsa import collect_alsa_data
from pipetune.collectors.bluetooth import collect_bluetooth_data
from pipetune.collectors.easyeffects import collect_easyeffects_data
from pipetune.collectors.pipewire import collect_pipewire_data
from pipetune.collectors.wireplumber import collect_wireplumber_data
from pipetune.models import RiskFinding
from pipetune.risk import build_recommendations, evaluate_risks, highest_risk, summarize_risks


def _metadata() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool_version": __version__,
        "codename": CODENAME,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def _service_state(command_result: dict) -> str:
    if not command_result.get("available"):
        return "unavailable"
    if command_result.get("timed_out"):
        return "timed_out"
    if command_result.get("exit_code") != 0:
        return command_result.get("stdout", "").strip() or "inactive"
    return command_result.get("stdout", "").strip() or "unknown"


def _collect_command_status(diagnostic: dict) -> list[dict]:
    command_items: list[tuple[str, str, dict | None]] = [
        ("pipewire", "pipewire", diagnostic["pipewire"]["services"]["pipewire"]),
        ("pipewire", "pipewire_pulse", diagnostic["pipewire"]["services"]["pipewire_pulse"]),
        ("pipewire", "pactl_get_default_sink", diagnostic["pipewire"]["pactl_get_default_sink"]),
        ("pipewire", "pactl_get_default_source", diagnostic["pipewire"]["pactl_get_default_source"]),
        ("pipewire", "wpctl_inspect_default_sink", diagnostic["pipewire"]["wpctl_inspect_default_sink"]),
        ("pipewire", "wpctl_inspect_default_source", diagnostic["pipewire"]["wpctl_inspect_default_source"]),
        ("pipewire", "pactl_info", diagnostic["pipewire"]["pactl_info"]),
        ("pipewire", "wpctl_status", diagnostic["pipewire"]["wpctl_status"]),
        ("pipewire", "pw_dump", diagnostic["pipewire"]["pw_dump"]),
        ("wireplumber", "service_status", diagnostic["wireplumber"]["service_status"]),
        ("wireplumber", "wpctl_status", diagnostic["wireplumber"]["wpctl_status"]),
        ("alsa", "aplay_list", diagnostic["alsa"]["aplay_list"]),
        ("alsa", "arecord_list", diagnostic["alsa"]["arecord_list"]),
        ("bluetooth", "pactl_cards", diagnostic["bluetooth"]["pactl_cards"]),
        ("easyeffects", "version", diagnostic["easyeffects"].get("version")),
    ]

    summary: list[dict] = []
    for component, name, result in command_items:
        if not result:
            continue
        summary.append(
            {
                "component": component,
                "name": name,
                "command": result.get("command"),
                "available": result.get("available"),
                "exit_code": result.get("exit_code"),
                "timed_out": result.get("timed_out"),
                "error": result.get("error"),
            }
        )
    return summary


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


def _render_route_line(route: dict, route_kind: str) -> str:
    if route.get("detected") and route.get("name"):
        return f"{route['name']} (from {_route_source_label(route.get('source', 'unknown'))})"
    return "unknown (route detection incomplete)"


def run_diagnostic() -> dict:
    pipewire = collect_pipewire_data()
    wireplumber = collect_wireplumber_data()
    alsa = collect_alsa_data()
    bluetooth = collect_bluetooth_data()
    easyeffects = collect_easyeffects_data()

    diagnostic = {
        "metadata": _metadata(),
        "pipewire": pipewire,
        "wireplumber": wireplumber,
        "alsa": alsa,
        "bluetooth": bluetooth,
        "easyeffects": easyeffects,
    }

    findings = evaluate_risks(diagnostic)
    recommendations = build_recommendations(diagnostic, findings)

    diagnostic["risks"] = [finding.to_dict() for finding in findings]
    diagnostic["recommendations"] = recommendations
    diagnostic["raw_command_status"] = _collect_command_status(diagnostic)

    return diagnostic


def render_doctor_summary(diagnostic: dict) -> str:
    pipewire_state = _service_state(diagnostic["pipewire"]["services"]["pipewire"])
    pipewire_pulse_state = _service_state(diagnostic["pipewire"]["services"]["pipewire_pulse"])
    wireplumber_state = _service_state(diagnostic["wireplumber"]["service_status"])

    playback_count = len(diagnostic["alsa"].get("playback_devices", []))
    capture_count = len(diagnostic["alsa"].get("capture_devices", []))
    cards_count = len(diagnostic["alsa"].get("cards", []))

    bluetooth_mode = diagnostic["bluetooth"].get("playback_mode", "not_active")
    easyeffects_installed = diagnostic["easyeffects"].get("installed", False)
    filter_chain = diagnostic["pipewire"].get("filter_chain_detected", False)

    findings = [RiskFinding(**item) for item in diagnostic["risks"]]
    risk_counts = summarize_risks(findings)
    highest = highest_risk(findings)
    next_step = diagnostic["recommendations"][0] if diagnostic["recommendations"] else "No recommendation generated."

    lines = [
        "PipeTune Linux doctor summary",
        f"- PipeWire: {pipewire_state}",
        f"- pipewire-pulse: {pipewire_pulse_state}",
        f"- WirePlumber: {wireplumber_state}",
        f"- Default sink: {_render_route_line(diagnostic['pipewire'].get('default_sink', {}), 'sink')}",
        f"- Default source: {_render_route_line(diagnostic['pipewire'].get('default_source', {}), 'source')}",
        f"- ALSA cards: {cards_count}",
        f"- ALSA playback devices: {playback_count}",
        f"- ALSA capture devices: {capture_count}",
        f"- Bluetooth audio mode: {bluetooth_mode}",
        f"- EasyEffects installed: {'yes' if easyeffects_installed else 'no'}",
        f"- PipeWire filter-chain active: {'yes' if filter_chain else 'no'}",
        (
            "- Risk counts: "
            + ", ".join(
                f"{severity}={risk_counts.get(severity, 0)}"
                for severity in ("critical", "high", "medium", "low", "info")
            )
        ),
        f"- Highest risk: {highest}",
        f"- Recommended next step: {next_step}",
    ]
    return "\n".join(lines)
