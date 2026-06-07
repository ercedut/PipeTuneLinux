"""WirePlumber rule install state queries (read-only)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.wireplumber.manifest import RuleManifestEntry, load_manifest
from pipetune.wireplumber.paths import get_manifest_path, get_wireplumber_rule_dir

_STATE_SAFETY_LINES = [
    "This command is read-only.",
    "No service was restarted.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class RuleStatusReport:
    manifest_path: str
    rule_dir: str
    active_count: int
    rolled_back_count: int
    broken_count: int
    entries: list[RuleManifestEntry] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.warnings:
            return "warn"
        return "pass"


def run_rule_status(manifest_path: Path | None = None) -> RuleStatusReport:
    """Return a read-only summary of all installed WirePlumber rules."""
    resolved_manifest_path = manifest_path or get_manifest_path()
    rule_dir = get_wireplumber_rule_dir()
    entries = load_manifest(resolved_manifest_path)

    active = [e for e in entries if e.status == "active"]
    rolled_back = [e for e in entries if e.status == "rolled_back"]
    broken = [e for e in entries if e.status == "broken"]
    checks: list[str] = []
    warnings: list[str] = []

    checks.append(f"manifest: {resolved_manifest_path}")
    checks.append(f"rule directory: {rule_dir}")
    checks.append(f"active rules: {len(active)}")
    checks.append(f"rolled_back rules: {len(rolled_back)}")
    checks.append(f"broken rules: {len(broken)}")

    if not resolved_manifest_path.exists():
        warnings.append("Manifest file does not exist yet; no rules have been installed.")

    return RuleStatusReport(
        manifest_path=str(resolved_manifest_path),
        rule_dir=str(rule_dir),
        active_count=len(active),
        rolled_back_count=len(rolled_back),
        broken_count=len(broken),
        entries=entries,
        checks=checks,
        warnings=warnings,
    )


def run_list_rules(manifest_path: Path | None = None) -> RuleStatusReport:
    """Return a read-only list of all WirePlumber rule manifest entries."""
    return run_rule_status(manifest_path=manifest_path)


def render_rule_status(report: RuleStatusReport) -> str:
    lines = ["PipeTune WirePlumber Rule Status", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    lines.extend(["", "Rules:"])
    if not report.entries:
        lines.append("  (no rules installed)")
    else:
        for entry in report.entries:
            lines.append(f"  [{entry.status}] {entry.install_id}  {entry.rule_id}  {entry.installed_path}")
    lines.extend(["", f"Verdict: {report.verdict}", *_STATE_SAFETY_LINES])
    return "\n".join(lines)


def render_list_rules(report: RuleStatusReport) -> str:
    lines = ["PipeTune WirePlumber List Rules", ""]
    if not report.entries:
        lines.append("No WirePlumber rules installed by PipeTune.")
    else:
        for entry in report.entries:
            lines.extend([
                f"install_id:  {entry.install_id}",
                f"rule_id:     {entry.rule_id}",
                f"status:      {entry.status}",
                f"destination: {entry.installed_path}",
                f"checksum:    {entry.checksum}",
                f"created_at:  {entry.created_at}",
                f"version:     {entry.pipetune_version}",
                "",
            ])
    lines.extend([f"Verdict: {report.verdict}", *_STATE_SAFETY_LINES])
    return "\n".join(lines)


def render_rule_status_json(report: RuleStatusReport) -> str:
    payload = {
        "command": "wireplumber rule-status",
        "verdict": report.verdict,
        "manifest_path": report.manifest_path,
        "rule_dir": report.rule_dir,
        "active_count": report.active_count,
        "rolled_back_count": report.rolled_back_count,
        "broken_count": report.broken_count,
        "entries": [e.as_dict() for e in report.entries],
        "checks": report.checks,
        "warnings": report.warnings,
        "safety": {
            "read_only": True,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_list_rules_json(report: RuleStatusReport) -> str:
    payload = {
        "command": "wireplumber list-rules",
        "verdict": report.verdict,
        "manifest_path": report.manifest_path,
        "rule_dir": report.rule_dir,
        "entries": [e.as_dict() for e in report.entries],
        "checks": report.checks,
        "warnings": report.warnings,
        "safety": {
            "read_only": True,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)
