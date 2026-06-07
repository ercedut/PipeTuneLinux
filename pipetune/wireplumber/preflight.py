"""WirePlumber install-preflight — read-only preflight check before install-rule.

All checks are read-only.  No files are created.  No services are restarted.
No audio routing is changed.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.wireplumber.integrity import run_state_doctor
from pipetune.wireplumber.paths import get_manifest_path, get_wireplumber_rule_dir

_REFUSED_SYSTEM_PREFIXES = ("/etc/", "/usr/", "/lib/", "/sys/")

_PREFLIGHT_SAFETY_LINES = [
    "This command is read-only.",
    "No file was created.",
    "No service was restarted.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class PreflightReport:
    wireplumber_service_status: str
    pipewire_service_status: str
    config_dir: str
    config_dir_exists: bool
    config_dir_writable: bool
    manifest_path: str
    manifest_accessible: bool
    existing_rule_state_verdict: str
    xdg_config_home_set: bool
    pipetune_home_set: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"

    @property
    def passed(self) -> bool:
        return self.verdict != "fail"


def _check_service_status(service: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True, text=True, timeout=5,
        )
        status = result.stdout.strip()
        return status if status else "unknown"
    except Exception:
        return "unknown"


def run_install_preflight(
    rule_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> PreflightReport:
    """Read-only preflight check before install-rule. Creates no files or directories."""
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    resolved_rule_dir = rule_dir or get_wireplumber_rule_dir()
    resolved_manifest_path = manifest_path or get_manifest_path()

    # Service status
    wp_status = _check_service_status("wireplumber")
    pw_status = _check_service_status("pipewire")
    checks.append(f"wireplumber service status: {wp_status}")
    checks.append(f"pipewire service status: {pw_status}")

    # System path safety
    for prefix in _REFUSED_SYSTEM_PREFIXES:
        if str(resolved_rule_dir).startswith(prefix):
            errors.append(f"config_dir is a system path (refused): {resolved_rule_dir}")
            break

    # Config dir
    config_dir_exists = resolved_rule_dir.exists()
    config_dir_writable = False
    checks.append(f"user-level WirePlumber config dir: {resolved_rule_dir}")
    checks.append(f"config dir exists: {config_dir_exists}")

    if config_dir_exists:
        config_dir_writable = os.access(resolved_rule_dir, os.W_OK)
        checks.append(f"config dir writable: {config_dir_writable}")
        if not config_dir_writable:
            errors.append(f"Config directory is not writable: {resolved_rule_dir}")
    else:
        parent = resolved_rule_dir.parent
        if parent.exists():
            config_dir_writable = os.access(parent, os.W_OK)
        checks.append(f"config dir writable (parent writable): {config_dir_writable}")
        warnings.append(
            f"Config directory does not exist yet: {resolved_rule_dir}. "
            "install-rule --confirm-install will create it."
        )

    # Manifest accessibility
    manifest_accessible = False
    if resolved_manifest_path.exists():
        manifest_accessible = os.access(resolved_manifest_path, os.R_OK | os.W_OK)
        checks.append(f"manifest path: {resolved_manifest_path}")
        checks.append(f"manifest readable/writable: {manifest_accessible}")
        if not manifest_accessible:
            errors.append(f"Manifest file exists but is not readable/writable: {resolved_manifest_path}")
    else:
        manifest_parent = resolved_manifest_path.parent
        if manifest_parent.exists():
            manifest_accessible = os.access(manifest_parent, os.W_OK)
        checks.append(f"manifest path: {resolved_manifest_path}")
        checks.append(f"manifest can be created (parent writable): {manifest_accessible}")
        if not manifest_accessible:
            warnings.append(
                f"Manifest parent directory does not exist or is not writable: {manifest_parent}. "
                "install-rule --confirm-install will create it."
            )

    # Existing rule state integrity
    state_report = run_state_doctor(
        manifest_path=resolved_manifest_path,
        rule_dir=resolved_rule_dir,
    )
    existing_state_verdict = state_report.verdict
    checks.append(f"existing PipeTune rule state: {existing_state_verdict}")
    if existing_state_verdict == "warn":
        warnings.append(
            "Existing rule state has warnings. "
            "Run: pipetune wireplumber rule-state-doctor for details."
        )
    elif existing_state_verdict == "fail":
        warnings.append(
            "Existing rule state has errors. "
            "Run: pipetune wireplumber rule-state-doctor for details."
        )

    # Test isolation env vars
    xdg_set = bool(os.environ.get("XDG_CONFIG_HOME"))
    pipetune_home_set = bool(os.environ.get("PIPETUNE_HOME"))
    checks.append(f"XDG_CONFIG_HOME set (test isolation active): {xdg_set}")
    checks.append(f"PIPETUNE_HOME set (test isolation active): {pipetune_home_set}")

    return PreflightReport(
        wireplumber_service_status=wp_status,
        pipewire_service_status=pw_status,
        config_dir=str(resolved_rule_dir),
        config_dir_exists=config_dir_exists,
        config_dir_writable=config_dir_writable,
        manifest_path=str(resolved_manifest_path),
        manifest_accessible=manifest_accessible,
        existing_rule_state_verdict=existing_state_verdict,
        xdg_config_home_set=xdg_set,
        pipetune_home_set=pipetune_home_set,
        checks=checks,
        warnings=warnings,
        errors=errors,
    )


def render_preflight_report(report: PreflightReport) -> str:
    lines = ["PipeTune WirePlumber Install Preflight", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *_PREFLIGHT_SAFETY_LINES])
    return "\n".join(lines)


def render_preflight_report_json(report: PreflightReport) -> str:
    payload = {
        "command": "wireplumber install-preflight",
        "verdict": report.verdict,
        "passed": report.passed,
        "wireplumber_service_status": report.wireplumber_service_status,
        "pipewire_service_status": report.pipewire_service_status,
        "config_dir": report.config_dir,
        "config_dir_exists": report.config_dir_exists,
        "config_dir_writable": report.config_dir_writable,
        "manifest_path": report.manifest_path,
        "manifest_accessible": report.manifest_accessible,
        "existing_rule_state_verdict": report.existing_rule_state_verdict,
        "xdg_config_home_set": report.xdg_config_home_set,
        "pipetune_home_set": report.pipetune_home_set,
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "safety": {
            "read_only": True,
            "wrote_files": False,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)
