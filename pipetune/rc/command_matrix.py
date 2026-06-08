"""PipeTune Linux RC command matrix — static safety/behavior reference for all CLI commands."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class CommandEntry:
    command: str
    category: str
    read_only: bool
    writes_repo_local: bool
    writes_user_config: bool
    requires_confirmation: bool
    has_dry_run: bool
    json_supported: bool
    safety_notes: str


_MATRIX: list[CommandEntry] = [
    CommandEntry("version", "info", True, False, False, False, False, False,
                 "Prints version and codename only."),
    CommandEntry("doctor", "info", True, False, False, False, False, False,
                 "Read-only system audio diagnostics."),
    CommandEntry("devices", "info", True, False, False, False, False, False,
                 "Read-only device listing."),
    CommandEntry("hardware hda-audit", "hardware", True, False, False, False, False, False,
                 "Read-only HDA codec audit."),
    CommandEntry("hardware mic-audit", "hardware", True, False, False, False, False, False,
                 "Read-only microphone audit."),
    CommandEntry("hardware gain-audit", "hardware", True, False, False, False, False, False,
                 "Read-only capture gain audit."),
    CommandEntry("hardware quirk-status", "hardware", True, False, False, False, False, False,
                 "Read-only hardware quirk status."),
    CommandEntry("hardware quirk-report", "hardware", False, True, False, False, False, False,
                 "Writes sanitized report bundle to repo-local directory."),
    CommandEntry("measure generate-sweep", "measure", False, False, False, False, False, False,
                 "Writes WAV to user-specified path; no system config written."),
    CommandEntry("measure analyze-sweep", "measure", False, False, False, False, False, False,
                 "Writes JSON to user-specified path; no system config written."),
    CommandEntry("measure inspect-wav", "measure", True, False, False, False, False, True,
                 "Read-only WAV inspection."),
    CommandEntry("measure import-rew", "measure", False, False, False, False, False, False,
                 "Writes normalized CSV to user-specified path."),
    CommandEntry("measure validate-response", "measure", True, False, False, False, False, True,
                 "Read-only response validation."),
    CommandEntry("measure compare-response", "measure", False, False, False, False, False, False,
                 "Writes comparison JSON to user-specified path."),
    CommandEntry("measure generate-correction", "measure", False, False, False, False, False, False,
                 "Writes draft TOML to user-specified path; not installed or applied."),
    CommandEntry("plugin info", "plugin", True, False, False, False, False, False,
                 "Read-only plugin info."),
    CommandEntry("plugin build", "plugin", False, True, False, True, False, False,
                 "Builds LV2 locally; requires --local. No global install."),
    CommandEntry("plugin clean", "plugin", False, True, False, True, False, False,
                 "Removes local LV2 build artifacts; requires --local."),
    CommandEntry("plugin validate", "plugin", True, False, False, True, False, True,
                 "Read-only validation; requires --metadata, --rt-safety, or --offline."),
    CommandEntry("package inspect", "package", True, False, False, False, False, False,
                 "Read-only package metadata inspection."),
    CommandEntry("package build-check", "package", True, False, False, False, False, False,
                 "Builds locally, inspects, and cleans up; no publish."),
    CommandEntry("package smoke-test", "package", True, False, False, False, False, False,
                 "Read-only CLI smoke checks."),
    CommandEntry("package artifact-check", "package", True, False, False, False, False, True,
                 "Read-only forbidden artifact detection."),
    CommandEntry("package clean-local", "package", False, True, False, False, True, False,
                 "Removes gitignored local dev artifacts; --dry-run available."),
    CommandEntry("release check", "release", True, False, False, False, False, True,
                 "Read-only release quality gates; no publish."),
    CommandEntry("profiles validate-db", "profiles", True, False, False, False, False, True,
                 "Read-only profile database validation."),
    CommandEntry("profiles list", "profiles", True, False, False, False, False, False,
                 "Read-only profile listing."),
    CommandEntry("profiles show", "profiles", True, False, False, False, False, False,
                 "Read-only profile detail."),
    CommandEntry("profiles search", "profiles", True, False, False, False, False, False,
                 "Read-only profile search."),
    CommandEntry("wireplumber audit", "wireplumber", True, False, False, False, False, True,
                 "Read-only WirePlumber/PipeWire state audit."),
    CommandEntry("wireplumber suggest-rule", "wireplumber", False, True, False, True, True, True,
                 "Writes preview to repo-local previews/ only; requires --dry-run --user-only."),
    CommandEntry("wireplumber validate-preview", "wireplumber", True, False, False, False, False, True,
                 "Read-only preview file validation."),
    CommandEntry("wireplumber install-rule", "wireplumber", False, False, True, True, True, True,
                 "Installs user-level WirePlumber rule; requires --user-only and --dry-run|--confirm-install."),
    CommandEntry("wireplumber rollback-rule", "wireplumber", False, False, True, True, True, True,
                 "Rolls back installed WirePlumber rule; requires --dry-run|--confirm-rollback."),
    CommandEntry("wireplumber rule-status", "wireplumber", True, False, False, False, False, True,
                 "Read-only rule install status."),
    CommandEntry("wireplumber list-rules", "wireplumber", True, False, False, False, False, True,
                 "Read-only installed rule listing."),
    CommandEntry("wireplumber rule-state-doctor", "wireplumber", True, False, False, False, False, True,
                 "Read-only rule state integrity check."),
    CommandEntry("wireplumber verify-rule", "wireplumber", True, False, False, False, False, True,
                 "Read-only rule verification."),
    CommandEntry("wireplumber repair-rule-state", "wireplumber", True, False, False, True, True, True,
                 "Dry-run only; proposes repairs without modifying files."),
    CommandEntry("wireplumber cleanup-rolled-back-rules", "wireplumber", False, False, True, True, True, True,
                 "Removes safe rolled-back manifest entries; requires --dry-run|--confirm-cleanup."),
    CommandEntry("wireplumber install-preflight", "wireplumber", True, False, False, False, False, True,
                 "Read-only preflight check before install-rule."),
    CommandEntry("wireplumber install-guide", "wireplumber", True, False, False, False, False, True,
                 "Read-only step-by-step install workflow guide."),
    CommandEntry("route audit", "route", True, False, False, False, False, True,
                 "Read-only PipeWire routing audit."),
    CommandEntry("route explain", "route", True, False, False, False, False, True,
                 "Read-only routing explanation in plain English."),
    CommandEntry("route recommend", "route", True, False, False, False, False, True,
                 "Read-only routing recommendations."),
    CommandEntry("bluetooth policy-audit", "bluetooth", True, False, False, False, False, True,
                 "Read-only Bluetooth audio policy audit."),
    CommandEntry("rc audit", "rc", True, False, False, False, False, True,
                 "Read-only release-candidate audit."),
    CommandEntry("rc command-matrix", "rc", True, False, False, False, False, True,
                 "Read-only command safety matrix."),
    CommandEntry("rc mutation-audit", "rc", True, False, False, False, False, True,
                 "Read-only static mutation safety scan."),
    CommandEntry("rc docs-check", "rc", True, False, False, False, False, True,
                 "Read-only documentation integrity check."),
    CommandEntry("rc fedora-smoke", "rc", True, False, False, False, False, True,
                 "Read-only non-mutating Fedora KDE smoke test suite."),
]

KNOWN_CATEGORIES = frozenset({
    "info", "hardware", "measure", "plugin", "package",
    "release", "profiles", "wireplumber", "route", "bluetooth", "rc",
})


@dataclass(slots=True)
class CommandMatrixReport:
    entries: list[CommandEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def run_command_matrix() -> CommandMatrixReport:
    errors: list[str] = []
    for entry in _MATRIX:
        if not entry.category:
            errors.append(f"command '{entry.command}' has blank category")
        elif entry.category not in KNOWN_CATEGORIES:
            errors.append(f"command '{entry.command}' has unknown category: {entry.category}")
    return CommandMatrixReport(entries=list(_MATRIX), errors=errors)


def render_command_matrix(report: CommandMatrixReport) -> str:
    lines = [
        "PipeTune RC Command Matrix",
        "",
        f"{'Command':<45} {'Category':<12} {'RO':<4} {'WRL':<4} {'WUC':<4} {'REQ':<4} {'DRY':<4} {'JSON':<5} Notes",
        "-" * 130,
    ]
    for entry in report.entries:
        ro = "yes" if entry.read_only else "no"
        wrl = "yes" if entry.writes_repo_local else "no"
        wuc = "yes" if entry.writes_user_config else "no"
        req = "yes" if entry.requires_confirmation else "no"
        dry = "yes" if entry.has_dry_run else "no"
        jsn = "yes" if entry.json_supported else "no"
        lines.append(
            f"{entry.command:<45} {entry.category:<12} {ro:<4} {wrl:<4} {wuc:<4} {req:<4} {dry:<4} {jsn:<5} {entry.safety_notes}"
        )
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {e}" for e in report.errors)
    lines.extend([
        "",
        f"Total commands: {len(report.entries)}",
        "",
        "Column key: RO=read_only, WRL=writes_repo_local, WUC=writes_user_config,",
        "            REQ=requires_confirmation, DRY=has_dry_run, JSON=json_supported",
        "",
        "No system configuration was modified.",
        "No audio routing was changed.",
    ])
    return "\n".join(lines)


def render_command_matrix_json(report: CommandMatrixReport) -> str:
    return json.dumps(
        {
            "command_matrix": [asdict(e) for e in report.entries],
            "total": len(report.entries),
            "errors": report.errors,
            "passed": report.passed,
            "safety": {
                "read_only": True,
                "modified_system": False,
                "changed_routing": False,
                "restarted_services": False,
                "wrote_user_audio_config": False,
            },
        },
        indent=2,
    )
