"""Rendering for WirePlumber and routing diagnostic reports."""

from __future__ import annotations

import json
import socket

import pipetune
from pipetune.wireplumber.models import RouteAuditReport, WirePlumberAuditReport

_SAFETY_DISCLAIMER = [
    "No system configuration was modified.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


def render_wireplumber_audit(report: WirePlumberAuditReport) -> str:
    lines = ["PipeTune WirePlumber Audit", ""]
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
    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for e in report.errors:
            lines.append(f"- fail: {e}")
    lines.append("")
    lines.append(f"Final verdict: {report.verdict}")
    lines.extend(_SAFETY_DISCLAIMER)
    return "\n".join(lines)


def render_wireplumber_audit_json(report: WirePlumberAuditReport) -> str:
    return json.dumps(
        {
            "command": "wireplumber audit",
            "pipetune_version": pipetune.__version__,
            "collected_at": report.collected_at,
            "host": _safe_hostname(),
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "default_sink": report.default_sink,
            "default_source": report.default_source,
            "sink_count": report.sink_count,
            "source_count": report.source_count,
            "card_count": report.card_count,
            "services": [
                {
                    "name": s.name,
                    "active": s.active,
                    "details": s.details,
                }
                for s in report.services
            ],
            "safety": {
                "read_only": True,
                "modified_system": False,
                "restarted_services": False,
                "changed_routing": False,
            },
        },
        indent=2,
    )


def render_route_audit(report: RouteAuditReport) -> str:
    lines = ["PipeTune Route Audit", ""]
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
    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for e in report.errors:
            lines.append(f"- fail: {e}")
    lines.append("")
    lines.append(f"Final verdict: {report.verdict}")
    lines.extend(_SAFETY_DISCLAIMER)
    return "\n".join(lines)


def render_route_audit_json(report: RouteAuditReport) -> str:
    return json.dumps(
        {
            "command": "route audit",
            "pipetune_version": pipetune.__version__,
            "collected_at": report.collected_at,
            "host": _safe_hostname(),
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "default_sink": report.default_sink,
            "default_source": report.default_source,
            "sink_count": report.sink_count,
            "source_count": report.source_count,
            "has_virtual_sinks": report.has_virtual_sinks,
            "has_pipetune_configs": report.has_pipetune_configs,
            "bluetooth_hfp_suspected": report.bluetooth_hfp_suspected,
            "safety": {
                "read_only": True,
                "modified_system": False,
                "restarted_services": False,
                "changed_routing": False,
            },
        },
        indent=2,
    )


def render_route_explain(lines: list[str]) -> str:
    return "\n".join(lines)


def render_route_explain_json(lines: list[str]) -> str:
    return json.dumps(
        {
            "command": "route explain",
            "pipetune_version": pipetune.__version__,
            "host": _safe_hostname(),
            "explanation": lines,
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
