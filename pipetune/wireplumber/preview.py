"""WirePlumber rule preview generation and validation for PipeTune Linux.

Rules are NEVER installed. This module only generates preview text
and validates that previews are safe repo-local files.
"""

from __future__ import annotations

import datetime
import json
import re
import socket
from dataclasses import dataclass, field
from pathlib import Path

import pipetune

_ALLOWED_OUTPUT_PREFIXES = (
    "previews/wireplumber/",
    "reports/wireplumber/",
)

_REPO_ROOT_RELATIVE = True

_DANGEROUS_LUA_PATTERNS = (
    r"\bos\.execute\b",
    r"\bio\.open\b",
    r"\bloadfile\b",
    r"\bloadstring\b",
    r"\brequire\b",
    r"\bdofile\b",
    r"\bpcall\b.*os\.",
    r"\bexecute\b",
    r"/etc/wireplumber",
    r"~/.config/wireplumber",
    r"\.config/wireplumber",
    r"/etc/pipewire",
)

_PREVIEW_REQUIRED_MARKERS = (
    "PREVIEW ONLY",
    "NOT INSTALLED",
)

_SAFETY_DISCLAIMER = [
    "No WirePlumber rule was installed.",
    "No system configuration was modified.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


@dataclass(slots=True)
class RulePreviewReport:
    passed: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    output_path: str = ""

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


@dataclass(slots=True)
class PreviewValidationReport:
    passed: bool
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    path: str = ""

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


def run_suggest_rule(
    dry_run: bool,
    user_only: bool,
    output_path: Path | None,
    repo_root: Path | None = None,
) -> RulePreviewReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    if not dry_run:
        errors.append(
            "suggest-rule refused: --dry-run is required. "
            "WirePlumber rule previews require explicit --dry-run acknowledgment."
        )
        return RulePreviewReport(passed=False, checks=checks, warnings=warnings, errors=errors)

    if not user_only:
        errors.append(
            "suggest-rule refused: --user-only is required. "
            "Only user-level (non-system) rule previews are supported."
        )
        return RulePreviewReport(passed=False, checks=checks, warnings=warnings, errors=errors)

    checks.append("--dry-run flag provided: preview mode confirmed")
    checks.append("--user-only flag provided: user-level scope only")

    resolved_root = repo_root or _find_repo_root()

    if output_path is not None:
        path_check = _validate_output_path(output_path, resolved_root)
        if path_check:
            errors.extend(path_check)
            return RulePreviewReport(passed=False, checks=checks, warnings=warnings, errors=errors)
        checks.append(f"output path validated as repo-local: {output_path}")

    preview_text = _generate_preview_text(output_path)
    checks.append("rule preview text generated (skeleton only — not a production rule)")
    warnings.append(
        "PREVIEW ONLY — NOT INSTALLED. "
        "This is a skeleton rule preview for review purposes. "
        "Do not apply this rule without understanding WirePlumber configuration. "
        "PipeTune does not install this rule automatically."
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(preview_text, encoding="utf-8")
        checks.append(f"preview written to: {output_path}")

    return RulePreviewReport(
        passed=True,
        checks=checks,
        warnings=warnings,
        errors=errors,
        output_path=str(output_path) if output_path else "",
    )


def run_validate_preview(
    path: Path,
    repo_root: Path | None = None,
) -> PreviewValidationReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    resolved_root = repo_root or _find_repo_root()

    if not path.exists():
        errors.append(f"preview file does not exist: {path}")
        return PreviewValidationReport(passed=False, checks=checks, warnings=warnings, errors=errors, path=str(path))

    checks.append(f"preview file exists: {path.name}")

    path_errors = _validate_output_path(path, resolved_root)
    if path_errors:
        errors.extend(path_errors)
    else:
        checks.append("preview path is repo-local allowed path")

    content = path.read_text(encoding="utf-8")

    for marker in _PREVIEW_REQUIRED_MARKERS:
        if marker in content:
            checks.append(f"preview contains required marker: {marker}")
        else:
            errors.append(f"preview is missing required safety marker: '{marker}'")

    dangerous = _check_dangerous_content(content)
    if dangerous:
        errors.extend(f"dangerous content detected: {d}" for d in dangerous)
    else:
        checks.append("no dangerous content patterns detected in preview")

    checks.append("preview validation is read-only: no files modified")

    return PreviewValidationReport(
        passed=not errors,
        checks=checks,
        warnings=warnings,
        errors=errors,
        path=str(path),
    )


def render_suggest_rule_report(report: RulePreviewReport) -> str:
    lines = ["PipeTune WirePlumber Suggest Rule", ""]
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


def render_suggest_rule_json(report: RulePreviewReport) -> str:
    return json.dumps(
        {
            "command": "wireplumber suggest-rule",
            "pipetune_version": pipetune.__version__,
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "output_path": report.output_path,
            "safety": {
                "read_only": True,
                "rule_installed": False,
                "modified_system": False,
                "restarted_services": False,
                "changed_routing": False,
            },
        },
        indent=2,
    )


def render_validate_preview_report(report: PreviewValidationReport) -> str:
    lines = ["PipeTune WirePlumber Validate Preview", ""]
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


def render_validate_preview_json(report: PreviewValidationReport) -> str:
    return json.dumps(
        {
            "command": "wireplumber validate-preview",
            "pipetune_version": pipetune.__version__,
            "verdict": report.verdict,
            "passed": report.passed,
            "path": report.path,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "safety": {
                "read_only": True,
                "modified_system": False,
            },
        },
        indent=2,
    )


def _validate_output_path(path: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    path_str = str(path).replace("\\", "/")

    home = Path.home()
    if str(path).startswith(str(home / ".config")):
        errors.append(
            f"output path refused: ~/.config paths are not allowed. "
            f"WirePlumber rules must not be written to ~/.config/wireplumber. "
            f"Path: {path}"
        )
        return errors

    for etc_prefix in ("/etc/", "/lib/", "/usr/", "/sys/", "/proc/"):
        if str(path).startswith(etc_prefix):
            errors.append(
                f"output path refused: system paths are not allowed. Path: {path}"
            )
            return errors

    try:
        rel = path.resolve().relative_to(repo_root.resolve())
        rel_str = str(rel).replace("\\", "/")
        if not any(rel_str.startswith(prefix) for prefix in _ALLOWED_OUTPUT_PREFIXES):
            errors.append(
                f"output path refused: path must be under {' or '.join(_ALLOWED_OUTPUT_PREFIXES)}. "
                f"Relative path: {rel_str}"
            )
    except ValueError:
        errors.append(
            f"output path refused: path is not inside the repository root. Path: {path}"
        )

    return errors


def _check_dangerous_content(content: str) -> list[str]:
    found: list[str] = []
    for pattern in _DANGEROUS_LUA_PATTERNS:
        if re.search(pattern, content):
            found.append(pattern)
    return found


def _generate_preview_text(output_path: Path | None) -> str:
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds")
    filename = output_path.name if output_path else "example-rule.lua"
    return f"""-- ============================================================
-- PREVIEW ONLY — NOT INSTALLED
-- ============================================================
-- PipeTune Linux WirePlumber Rule Preview
-- Generated: {now}
-- PipeTune version: {pipetune.__version__}
-- File: {filename}
--
-- WARNING: This is a skeleton rule preview for review only.
-- PipeTune does NOT install this rule automatically.
-- Do NOT copy this file to ~/.config/wireplumber/ without
-- understanding WirePlumber configuration and the impact
-- of this rule on your audio setup.
--
-- This file was generated by: pipetune wireplumber suggest-rule --dry-run --user-only
-- Rollback: delete this file and restart WirePlumber if installed manually.
-- PipeTune does not install, load, or activate this rule.
-- ============================================================

-- Diagnostic summary:
-- Rule type: placeholder (no real audio policy generated in v0.8.1)
-- Reason: WirePlumber policy rule generation requires validated diagnostics
--         and explicit user authorization. Future versions will fill this in.

-- table rule_skeleton = {{
--   matches = {{
--     {{
--       {{ "node.name", "equals", "YOUR_DEVICE_NAME_HERE" }},
--     }},
--   }},
--   apply_properties = {{
--     ["audio.allowed-rates"] = "48000",
--   }},
-- }}

-- This is a skeleton only. Edit carefully before any manual use.
-- Reference: https://pipewire.pages.freedesktop.org/wireplumber/lua-api/
"""


def _find_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
