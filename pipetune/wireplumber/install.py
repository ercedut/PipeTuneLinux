"""WirePlumber user-level rule installation.

Installation requires --user-only and either --dry-run or --confirm-install.
Dry-run writes nothing. Confirmed install writes only under the user-level
WirePlumber config directory derived from XDG_CONFIG_HOME (or PIPETUNE_HOME
for the manifest). No service is restarted and no routing is changed.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pipetune import __version__
from pipetune.wireplumber.manifest import RuleManifestEntry, get_entry, load_manifest, save_manifest
from pipetune.wireplumber.paths import (
    get_manifest_path,
    get_wireplumber_rule_dir,
    make_rule_filename,
)
from pipetune.wireplumber.preview import _DANGEROUS_LUA_PATTERNS, _PREVIEW_REQUIRED_MARKERS

_REFUSED_PATH_PREFIXES = ("/etc/", "/usr/", "/lib/", "/sys/")
_INSTALL_SAFETY_LINES = [
    "No service was restarted.",
    "The installed rule will not take effect until you manually reload or restart WirePlumber.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified beyond the install.",
]


@dataclass(slots=True)
class InstallReport:
    dry_run: bool
    passed: bool
    install_id: str
    rule_id: str
    source_preview_path: str
    destination_path: str
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


def run_install_rule(
    preview_path: str,
    *,
    user_only: bool,
    dry_run: bool,
    confirm_install: bool,
    rule_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> InstallReport:
    """Install a WirePlumber rule from a validated preview file."""
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    install_id = uuid.uuid4().hex[:8]
    rule_id = f"pipetune-rule-{install_id}"
    resolved_rule_dir = rule_dir or get_wireplumber_rule_dir()
    resolved_manifest_path = manifest_path or get_manifest_path()

    def _fail(msg: str) -> InstallReport:
        errors.append(msg)
        return InstallReport(
            dry_run=dry_run, passed=False,
            install_id=install_id, rule_id=rule_id,
            source_preview_path=preview_path,
            destination_path="",
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )

    if not user_only:
        return _fail("--user-only is required for install-rule.")
    if dry_run and confirm_install:
        return _fail("Cannot pass both --dry-run and --confirm-install.")
    if not dry_run and not confirm_install:
        return _fail("Must pass either --dry-run or --confirm-install.")

    preview_str = preview_path
    for prefix in _REFUSED_PATH_PREFIXES:
        if preview_str.startswith(prefix):
            return _fail(f"Refused: preview source path is a system path: {preview_str}")

    try:
        Path(preview_str).resolve().relative_to((Path.home() / ".config" / "wireplumber").resolve())
        return _fail(f"Refused: preview source path is under ~/.config/wireplumber: {preview_str}")
    except ValueError:
        pass

    preview = Path(preview_path)
    if not preview.exists():
        return _fail(f"Preview file not found: {preview_str}")

    checks.append(f"preview file exists: {preview_str}")
    content = preview.read_text(encoding="utf-8")

    for marker in _PREVIEW_REQUIRED_MARKERS:
        if marker not in content:
            errors.append(f"Preview file missing required safety marker: {marker}")
    if errors:
        return InstallReport(
            dry_run=dry_run, passed=False,
            install_id=install_id, rule_id=rule_id,
            source_preview_path=preview_path,
            destination_path="",
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )
    checks.append("preview has required safety markers (PREVIEW ONLY, NOT INSTALLED)")

    for pattern in _DANGEROUS_LUA_PATTERNS:
        if re.search(pattern, content):
            return _fail(f"Preview file contains dangerous Lua pattern: {pattern}")
    checks.append("preview passes dangerous pattern scan")

    checksum = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()

    # v0.9.1: duplicate install protection
    existing_all = load_manifest(resolved_manifest_path)
    for existing_entry in existing_all:
        if existing_entry.status == "active" and existing_entry.checksum == checksum:
            return _fail(
                f"Duplicate install refused: a rule with the same checksum is already active "
                f"(install_id: {existing_entry.install_id}, rule_id: {existing_entry.rule_id})."
            )

    filename = make_rule_filename(install_id)
    destination = resolved_rule_dir / filename

    checks.append(f"destination: {destination}")
    checks.append(f"manifest: {resolved_manifest_path}")

    if dry_run:
        warnings.append(
            "Dry run: no files were written. "
            "Run with --confirm-install to install."
        )
        return InstallReport(
            dry_run=True, passed=True,
            install_id=install_id, rule_id=rule_id,
            source_preview_path=preview_path,
            destination_path=str(destination),
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )

    resolved_rule_dir.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    checks.append(f"rule file written: {destination}")

    now = datetime.now(timezone.utc).isoformat()
    entry = RuleManifestEntry(
        install_id=install_id,
        rule_id=rule_id,
        source_preview_path=str(preview.resolve()),
        installed_path=str(destination.resolve()),
        checksum=checksum,
        status="active",
        created_at=now,
        pipetune_version=__version__,
    )
    existing = load_manifest(resolved_manifest_path)
    existing.append(entry)
    save_manifest(resolved_manifest_path, existing)
    checks.append(f"manifest entry written: {resolved_manifest_path}")

    warnings.append(
        "No service was restarted. "
        "The installed rule will not take effect until you manually reload or restart WirePlumber."
    )
    return InstallReport(
        dry_run=False, passed=True,
        install_id=install_id, rule_id=rule_id,
        source_preview_path=preview_path,
        destination_path=str(destination),
        manifest_path=str(resolved_manifest_path),
        checks=checks, warnings=warnings, errors=errors,
    )


def render_install_report(report: InstallReport) -> str:
    mode = "Dry Run" if report.dry_run else "Install"
    lines = [f"PipeTune WirePlumber Rule {mode}", ""]
    if report.install_id:
        lines.append(f"install_id: {report.install_id}")
        lines.append(f"rule_id: {report.rule_id}")
    if report.destination_path:
        lines.append(f"destination: {report.destination_path}")
        lines.append(f"manifest: {report.manifest_path}")
    lines.extend(["", "Checks:"])
    lines.extend(f"- pass: {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *_INSTALL_SAFETY_LINES])
    if not report.dry_run and report.passed:
        lines.extend([
            "",
            f"To rollback: pipetune wireplumber rollback-rule {report.install_id} --dry-run",
        ])
    return "\n".join(lines)


def render_install_report_json(report: InstallReport) -> str:
    payload = {
        "command": "wireplumber install-rule",
        "dry_run": report.dry_run,
        "verdict": report.verdict,
        "passed": report.passed,
        "install_id": report.install_id,
        "rule_id": report.rule_id,
        "source_preview_path": report.source_preview_path,
        "destination_path": report.destination_path,
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
