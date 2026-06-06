"""Route recommendation engine for PipeTune Linux.

Produces read-only recommendations based on observed routing state.
No changes are made by this module.
"""

from __future__ import annotations

import datetime
import json
import socket
from dataclasses import dataclass, field

import pipetune
from pipetune.wireplumber.collect import (
    collect_pactl_info,
    collect_pactl_sinks,
    collect_wpctl_status,
)
from pipetune.wireplumber.diagnose import (
    _detect_bluetooth_profile,
    _detect_pipetune_configs,
    _detect_virtual_sinks,
    _parse_default_sink,
    _parse_default_source,
    _count_sink_blocks,
)

_SAFETY_DISCLAIMER = [
    "No routing was changed.",
    "No system configuration was modified.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class RouteRecommendReport:
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    collected_at: str = ""

    @property
    def verdict(self) -> str:
        if self.warnings:
            return "warn"
        return "pass"

    @property
    def passed(self) -> bool:
        return True


def run_route_recommend(
    pactl_info: str | None = None,
    pactl_sinks: str | None = None,
    wpctl_status: str | None = None,
) -> RouteRecommendReport:
    checks: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds")

    if pactl_info is None:
        ok, pactl_info = collect_pactl_info()
        if not ok:
            pactl_info = ""

    if pactl_sinks is None:
        ok, pactl_sinks = collect_pactl_sinks()
        if not ok:
            pactl_sinks = ""

    if wpctl_status is None:
        ok, wpctl_status = collect_wpctl_status()
        if not ok:
            wpctl_status = ""

    default_sink = _parse_default_sink(pactl_info)
    default_source = _parse_default_source(pactl_info)

    if default_sink:
        checks.append(f"default sink observed: {default_sink}")
    else:
        warnings.append("default sink is missing or unknown")
        recommendations.append(
            "Default sink is missing or unknown. "
            "Check that PipeWire and WirePlumber are running: "
            "pipetune wireplumber audit"
        )

    if default_source:
        checks.append(f"default source observed: {default_source}")
    else:
        warnings.append("default source is missing or unknown")

    bt_profile = _detect_bluetooth_profile(wpctl_status)
    if bt_profile == "hfp_hsp":
        warnings.append("Bluetooth device appears to be in HSP/HFP profile")
        recommendations.append(
            "Bluetooth device appears to be in HSP/HFP profile. "
            "For music playback, A2DP is usually preferred. "
            "To check: pipetune bluetooth policy-audit. "
            "To switch profiles manually: pactl set-card-profile <card-id> <profile-name> "
            "(PipeTune does not do this automatically)."
        )
    elif bt_profile == "a2dp":
        checks.append("Bluetooth route: A2DP profile (no action needed)")
    elif bt_profile == "bluetooth_present":
        warnings.append("Bluetooth device detected but profile is unknown")
        recommendations.append(
            "Bluetooth device is present but its profile could not be determined. "
            "Run: pipetune bluetooth policy-audit for details."
        )

    has_virtual = _detect_virtual_sinks(pactl_sinks)
    has_pipetune = _detect_pipetune_configs(pactl_sinks, wpctl_status)

    if has_pipetune:
        checks.append("PipeTune filter-chain config appears active")
    elif has_virtual:
        checks.append("virtual filter-chain sink(s) detected (not PipeTune-specific)")
    else:
        checks.append("no virtual filter-chain sinks detected")

    sink_count = _count_sink_blocks(pactl_sinks)
    if sink_count == 0:
        warnings.append("no audio sinks detected; output routing may be broken")
        recommendations.append(
            "No audio sinks detected. "
            "Check PipeWire and WirePlumber are running: pipetune wireplumber audit."
        )
    else:
        checks.append(f"sinks detected: {sink_count}")

    if not warnings and not recommendations:
        checks.append("no route mismatch detected; no recommendations at this time")

    checks.append("route recommend is read-only: no routing changed, no config modified")

    return RouteRecommendReport(
        checks=checks,
        warnings=warnings,
        recommendations=recommendations,
        collected_at=now,
    )


def render_route_recommend(report: RouteRecommendReport) -> str:
    lines = ["PipeTune Route Recommendations", ""]
    lines.append("Checks:")
    for check in report.checks:
        lines.append(f"- pass: {check}")
    if not report.checks:
        lines.append("- none")
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"- warn: {w}")
    if report.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
    lines.append("")
    lines.append(f"Final verdict: {report.verdict}")
    lines.append("Manual review required for any routing changes.")
    lines.extend(_SAFETY_DISCLAIMER)
    return "\n".join(lines)


def render_route_recommend_json(report: RouteRecommendReport) -> str:
    return json.dumps(
        {
            "command": "route recommend",
            "pipetune_version": pipetune.__version__,
            "collected_at": report.collected_at,
            "host": _safe_hostname(),
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
            "safety": {
                "read_only": True,
                "modified_system": False,
                "restarted_services": False,
                "changed_routing": False,
            },
        },
        indent=2,
    )


def _safe_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"
