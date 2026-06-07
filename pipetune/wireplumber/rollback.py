"""WirePlumber user-level rule rollback.

Rollback removes only the PipeTune-owned installed rule file and marks the
manifest entry as rolled_back.  No service is restarted and no routing is
changed.  Non-PipeTune files are never touched.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pipetune.wireplumber.manifest import RuleManifestEntry, get_entry, load_manifest, save_manifest
from pipetune.wireplumber.paths import get_manifest_path

_ROLLBACK_SAFETY_LINES = [
    "No service was restarted.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified beyond the rollback.",
]


@dataclass(slots=True)
class RollbackReport:
    dry_run: bool
    passed: bool
    install_id: str
    installed_path: str
    manifest_path: str
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if not self.passed:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


def run_rollback_rule(
    install_id: str,
    *,
    dry_run: bool,
    confirm_rollback: bool,
    manifest_path: Path | None = None,
) -> RollbackReport:
    """Rollback an installed WirePlumber rule by install_id."""
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    resolved_manifest_path = manifest_path or get_manifest_path()

    def _fail(msg: str) -> RollbackReport:
        errors.append(msg)
        return RollbackReport(
            dry_run=dry_run, passed=False,
            install_id=install_id, installed_path="",
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )

    if dry_run and confirm_rollback:
        return _fail("Cannot pass both --dry-run and --confirm-rollback.")
    if not dry_run and not confirm_rollback:
        return _fail("Must pass either --dry-run or --confirm-rollback.")

    entries = load_manifest(resolved_manifest_path)
    entry = get_entry(entries, install_id)

    if entry is None:
        return _fail(f"Unknown install_id: {install_id}")
    if entry.status == "rolled_back":
        return _fail(f"install_id {install_id} is already rolled back.")

    checks.append(f"install_id found: {install_id}")
    checks.append(f"status: {entry.status}")
    installed = Path(entry.installed_path)

    if dry_run:
        if installed.exists():
            checks.append(f"installed file exists: {installed}")
        else:
            warnings.append(f"Installed file not found (already missing): {installed}")
        warnings.append(
            "Dry run: no files were modified. "
            "Run with --confirm-rollback to rollback."
        )
        return RollbackReport(
            dry_run=True, passed=True,
            install_id=install_id, installed_path=str(installed),
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )

    if installed.exists():
        # v0.9.1: checksum mismatch protection — don't delete files that don't match manifest
        try:
            actual_checksum = "sha256:" + hashlib.sha256(installed.read_bytes()).hexdigest()
            if actual_checksum != entry.checksum:
                errors.append(
                    f"Checksum mismatch for {installed}; "
                    "file may have been modified manually. "
                    "Rollback refused to avoid deleting an unexpected file. "
                    "Review manually."
                )
                return RollbackReport(
                    dry_run=dry_run, passed=False,
                    install_id=install_id, installed_path=str(installed),
                    manifest_path=str(resolved_manifest_path),
                    checks=checks, warnings=warnings, errors=errors,
                )
        except OSError as exc:
            return _fail(f"Could not read installed rule for checksum check {installed}: {exc}")
        try:
            installed.unlink()
            checks.append(f"removed installed rule: {installed}")
        except OSError as exc:
            return _fail(f"Could not remove installed rule {installed}: {exc}")
    else:
        warnings.append(f"Installed file was already missing: {installed}")

    now = datetime.now(timezone.utc).isoformat()
    updated = []
    for e in entries:
        if e.install_id == install_id:
            updated.append(RuleManifestEntry(
                install_id=e.install_id,
                rule_id=e.rule_id,
                source_preview_path=e.source_preview_path,
                installed_path=e.installed_path,
                checksum=e.checksum,
                status="rolled_back",
                created_at=e.created_at,
                pipetune_version=e.pipetune_version,
                rolled_back_at=now,
            ))
        else:
            updated.append(e)
    save_manifest(resolved_manifest_path, updated)
    checks.append(f"manifest updated: {resolved_manifest_path}")

    return RollbackReport(
        dry_run=False, passed=True,
        install_id=install_id, installed_path=str(installed),
        manifest_path=str(resolved_manifest_path),
        checks=checks, warnings=warnings, errors=errors,
    )


def render_rollback_report(report: RollbackReport) -> str:
    mode = "Dry Run" if report.dry_run else "Rollback"
    lines = [f"PipeTune WirePlumber Rule {mode}", ""]
    lines.append(f"install_id: {report.install_id}")
    if report.installed_path:
        lines.append(f"installed path: {report.installed_path}")
    lines.append(f"manifest: {report.manifest_path}")
    lines.extend(["", "Checks:"])
    lines.extend(f"- pass: {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *_ROLLBACK_SAFETY_LINES])
    return "\n".join(lines)


def render_rollback_report_json(report: RollbackReport) -> str:
    payload = {
        "command": "wireplumber rollback-rule",
        "dry_run": report.dry_run,
        "verdict": report.verdict,
        "passed": report.passed,
        "install_id": report.install_id,
        "installed_path": report.installed_path,
        "manifest_path": report.manifest_path,
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "safety": {
            "user_level_only": True,
            "system_level": False,
            "restarted_services": False,
            "changed_routing": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)
