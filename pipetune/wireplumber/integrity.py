"""WirePlumber rule install state integrity checks (v0.9.1).

All commands in this module are read-only except cleanup-rolled-back-rules
with --confirm-cleanup, which removes only manifest entries whose status is
rolled_back and whose installed file is absent.  No service is restarted and
no routing is changed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.wireplumber.manifest import RuleManifestEntry, get_entry, load_manifest, save_manifest
from pipetune.wireplumber.paths import (
    get_manifest_path,
    get_wireplumber_rule_dir,
    is_pipetune_rule_filename,
)

_INTEGRITY_SAFETY_LINES = [
    "No service was restarted.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EntryIntegrity:
    install_id: str
    rule_id: str
    status: str
    installed_path: str
    file_exists: bool
    checksum_state: str
    problems: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StateDoctorReport:
    manifest_path: str
    rule_dir: str
    active_count: int
    rolled_back_count: int
    broken_count: int
    missing_file_count: int
    orphan_file_count: int
    checksum_mismatch_count: int
    duplicate_rule_count: int
    entries: list[EntryIntegrity] = field(default_factory=list)
    orphan_files: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if (self.warnings or self.missing_file_count or self.orphan_file_count
                or self.checksum_mismatch_count or self.duplicate_rule_count):
            return "warn"
        return "pass"


@dataclass(slots=True)
class VerifyRuleReport:
    install_id: str
    rule_id: str
    status: str
    installed_path: str
    file_exists: bool
    checksum_state: str
    manifest_path: str
    problems: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.errors or any(p in ("missing_file", "checksum_mismatch") for p in self.problems):
            return "fail"
        if self.warnings or self.problems:
            return "warn"
        return "pass"

    @property
    def passed(self) -> bool:
        return self.verdict != "fail"


@dataclass(slots=True)
class RepairReport:
    dry_run: bool
    manifest_path: str
    proposed_actions: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "pass"


@dataclass(slots=True)
class CleanupReport:
    dry_run: bool
    manifest_path: str
    removed_count: int
    planned_count: int
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
        return not self.errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_file_checksum(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _inspect_entry(entry: RuleManifestEntry) -> EntryIntegrity:
    installed = Path(entry.installed_path)
    problems: list[str] = []
    file_exists = installed.exists()
    checksum_state = "not_applicable"

    if file_exists:
        try:
            actual = _compute_file_checksum(installed)
            checksum_state = "valid" if actual == entry.checksum else "checksum_mismatch"
        except OSError:
            checksum_state = "unreadable"
    elif entry.status == "active":
        checksum_state = "missing"
        problems.append("missing_file")
    elif entry.status == "rolled_back":
        checksum_state = "not_applicable"

    if entry.status == "active" and checksum_state == "checksum_mismatch":
        problems.append("checksum_mismatch")
    if entry.status == "rolled_back" and file_exists:
        problems.append("rolled_back_file_still_present")

    return EntryIntegrity(
        install_id=entry.install_id,
        rule_id=entry.rule_id,
        status=entry.status,
        installed_path=entry.installed_path,
        file_exists=file_exists,
        checksum_state=checksum_state,
        problems=problems,
    )


def _find_orphan_files(rule_dir: Path, manifest_entries: list[RuleManifestEntry]) -> list[str]:
    if not rule_dir.exists():
        return []
    known_paths = {str(Path(e.installed_path).resolve()) for e in manifest_entries}
    orphans = []
    for path in sorted(rule_dir.iterdir()):
        if is_pipetune_rule_filename(path.name) and str(path.resolve()) not in known_paths:
            orphans.append(str(path))
    return orphans


def _find_duplicate_rule_ids(entries: list[RuleManifestEntry]) -> list[str]:
    from collections import Counter
    active = [e for e in entries if e.status == "active"]
    counts = Counter(e.rule_id for e in active)
    return [rule_id for rule_id, count in counts.items() if count > 1]


# ---------------------------------------------------------------------------
# State doctor
# ---------------------------------------------------------------------------

def run_state_doctor(
    manifest_path: Path | None = None,
    rule_dir: Path | None = None,
) -> StateDoctorReport:
    """Read-only state integrity check for all installed WirePlumber rules."""
    resolved_manifest_path = manifest_path or get_manifest_path()
    resolved_rule_dir = rule_dir or get_wireplumber_rule_dir()
    entries = load_manifest(resolved_manifest_path)

    inspected = [_inspect_entry(e) for e in entries]
    orphan_files = _find_orphan_files(resolved_rule_dir, entries)
    duplicate_rule_ids = _find_duplicate_rule_ids(entries)

    active = [e for e in entries if e.status == "active"]
    rolled_back = [e for e in entries if e.status == "rolled_back"]
    broken = [e for e in entries if e.status == "broken"]
    missing_file_count = sum(1 for i in inspected if "missing_file" in i.problems)
    checksum_mismatch_count = sum(1 for i in inspected if "checksum_mismatch" in i.problems)

    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    checks.append(f"manifest: {resolved_manifest_path}")
    checks.append(f"rule directory: {resolved_rule_dir}")
    checks.append(f"active: {len(active)}")
    checks.append(f"rolled_back: {len(rolled_back)}")
    checks.append(f"broken: {len(broken)}")
    checks.append(f"missing installed file: {missing_file_count}")
    checks.append(f"orphan PipeTune files: {len(orphan_files)}")
    checks.append(f"checksum mismatches: {checksum_mismatch_count}")
    checks.append(f"duplicate rule_ids: {len(duplicate_rule_ids)}")

    if missing_file_count:
        warnings.append(f"{missing_file_count} active rule(s) have missing installed files; run repair-rule-state --dry-run to review.")
    if checksum_mismatch_count:
        warnings.append(f"{checksum_mismatch_count} rule(s) have checksum mismatches; review manually before acting.")
    if orphan_files:
        warnings.append(f"{len(orphan_files)} orphan PipeTune rule file(s) found in rule directory; run repair-rule-state --dry-run to review.")
    if duplicate_rule_ids:
        warnings.append(f"Duplicate active rule_id(s) detected: {', '.join(duplicate_rule_ids)}")

    return StateDoctorReport(
        manifest_path=str(resolved_manifest_path),
        rule_dir=str(resolved_rule_dir),
        active_count=len(active),
        rolled_back_count=len(rolled_back),
        broken_count=len(broken),
        missing_file_count=missing_file_count,
        orphan_file_count=len(orphan_files),
        checksum_mismatch_count=checksum_mismatch_count,
        duplicate_rule_count=len(duplicate_rule_ids),
        entries=inspected,
        orphan_files=orphan_files,
        checks=checks,
        warnings=warnings,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Verify rule
# ---------------------------------------------------------------------------

def run_verify_rule(
    install_id: str,
    manifest_path: Path | None = None,
) -> VerifyRuleReport:
    """Read-only verification of a single installed WirePlumber rule."""
    resolved_manifest_path = manifest_path or get_manifest_path()
    entries = load_manifest(resolved_manifest_path)
    entry = get_entry(entries, install_id)

    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    if entry is None:
        errors.append(f"Unknown install_id: {install_id}")
        return VerifyRuleReport(
            install_id=install_id, rule_id="", status="", installed_path="",
            file_exists=False, checksum_state="unknown",
            manifest_path=str(resolved_manifest_path),
            checks=checks, warnings=warnings, errors=errors,
        )

    integrity = _inspect_entry(entry)
    checks.append(f"install_id: {install_id}")
    checks.append(f"rule_id: {entry.rule_id}")
    checks.append(f"status: {entry.status}")
    checks.append(f"installed_path: {entry.installed_path}")
    checks.append(f"file_exists: {integrity.file_exists}")
    checks.append(f"checksum_state: {integrity.checksum_state}")

    if "missing_file" in integrity.problems:
        errors.append(f"Installed file is missing: {entry.installed_path}")
    if "checksum_mismatch" in integrity.problems:
        warnings.append(f"Checksum mismatch for {entry.installed_path}; file may have been modified manually.")

    return VerifyRuleReport(
        install_id=entry.install_id,
        rule_id=entry.rule_id,
        status=entry.status,
        installed_path=entry.installed_path,
        file_exists=integrity.file_exists,
        checksum_state=integrity.checksum_state,
        manifest_path=str(resolved_manifest_path),
        problems=integrity.problems,
        checks=checks,
        warnings=warnings,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Repair dry-run
# ---------------------------------------------------------------------------

def run_repair_rule_state(manifest_path: Path | None = None, rule_dir: Path | None = None) -> RepairReport:
    """Dry-run only: propose repair actions without modifying any files."""
    resolved_manifest_path = manifest_path or get_manifest_path()
    resolved_rule_dir = rule_dir or get_wireplumber_rule_dir()
    entries = load_manifest(resolved_manifest_path)

    proposed: list[str] = []
    checks: list[str] = []
    warnings: list[str] = []

    checks.append(f"manifest: {resolved_manifest_path}")

    for entry in entries:
        integrity = _inspect_entry(entry)
        if "missing_file" in integrity.problems:
            proposed.append(
                f"Mark entry {entry.install_id} ({entry.rule_id}) as broken "
                f"(installed file missing: {entry.installed_path})"
            )
        if "checksum_mismatch" in integrity.problems:
            proposed.append(
                f"Review entry {entry.install_id} ({entry.rule_id}): "
                f"checksum mismatch at {entry.installed_path} — manual review required before action"
            )

    orphan_files = _find_orphan_files(resolved_rule_dir, entries)
    for orphan in orphan_files:
        proposed.append(f"Remove orphan PipeTune rule file (not in manifest): {orphan}")

    for entry in entries:
        if entry.status == "rolled_back" and not Path(entry.installed_path).exists():
            proposed.append(
                f"Cleanup safe rolled_back manifest entry {entry.install_id} "
                f"(file already absent): run cleanup-rolled-back-rules --confirm-cleanup"
            )

    if not proposed:
        checks.append("no repair actions proposed; state appears clean")
    else:
        warnings.append(f"{len(proposed)} repair action(s) proposed (dry run only — no changes made).")

    return RepairReport(
        dry_run=True,
        manifest_path=str(resolved_manifest_path),
        proposed_actions=proposed,
        checks=checks,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Cleanup rolled-back entries
# ---------------------------------------------------------------------------

def run_cleanup_rolled_back(
    *,
    dry_run: bool,
    confirm_cleanup: bool,
    manifest_path: Path | None = None,
) -> CleanupReport:
    """Remove manifest entries where status==rolled_back and file is absent."""
    resolved_manifest_path = manifest_path or get_manifest_path()
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    def _fail(msg: str) -> CleanupReport:
        errors.append(msg)
        return CleanupReport(
            dry_run=dry_run, manifest_path=str(resolved_manifest_path),
            removed_count=0, planned_count=0,
            checks=checks, warnings=warnings, errors=errors,
        )

    if dry_run and confirm_cleanup:
        return _fail("Cannot pass both --dry-run and --confirm-cleanup.")
    if not dry_run and not confirm_cleanup:
        return _fail("Must pass either --dry-run or --confirm-cleanup.")

    entries = load_manifest(resolved_manifest_path)
    safe_to_remove = [
        e for e in entries
        if e.status == "rolled_back" and not Path(e.installed_path).exists()
    ]
    checks.append(f"manifest entries: {len(entries)}")
    checks.append(f"safe-to-cleanup rolled_back entries: {len(safe_to_remove)}")

    if dry_run:
        for e in safe_to_remove:
            checks.append(f"would remove: {e.install_id} ({e.rule_id})")
        warnings.append("Dry run: no manifest entries were removed.")
        return CleanupReport(
            dry_run=True, manifest_path=str(resolved_manifest_path),
            removed_count=0, planned_count=len(safe_to_remove),
            checks=checks, warnings=warnings, errors=errors,
        )

    ids_to_remove = {e.install_id for e in safe_to_remove}
    kept = [e for e in entries if e.install_id not in ids_to_remove]
    save_manifest(resolved_manifest_path, kept)
    for e in safe_to_remove:
        checks.append(f"removed manifest entry: {e.install_id} ({e.rule_id})")

    return CleanupReport(
        dry_run=False, manifest_path=str(resolved_manifest_path),
        removed_count=len(safe_to_remove), planned_count=len(safe_to_remove),
        checks=checks, warnings=warnings, errors=errors,
    )


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

def render_state_doctor(report: StateDoctorReport) -> str:
    lines = ["PipeTune WirePlumber Rule State Doctor", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    if report.orphan_files:
        lines.extend(["", "Orphan files:"])
        lines.extend(f"  {f}" for f in report.orphan_files)
    lines.extend(["", f"Final verdict: {report.verdict}", *_INTEGRITY_SAFETY_LINES])
    return "\n".join(lines)


def render_state_doctor_json(report: StateDoctorReport) -> str:
    payload = {
        "command": "wireplumber rule-state-doctor",
        "verdict": report.verdict,
        "manifest_path": report.manifest_path,
        "rule_dir": report.rule_dir,
        "active_count": report.active_count,
        "rolled_back_count": report.rolled_back_count,
        "broken_count": report.broken_count,
        "missing_file_count": report.missing_file_count,
        "orphan_file_count": report.orphan_file_count,
        "checksum_mismatch_count": report.checksum_mismatch_count,
        "duplicate_rule_count": report.duplicate_rule_count,
        "orphan_files": report.orphan_files,
        "entries": [
            {
                "install_id": e.install_id,
                "rule_id": e.rule_id,
                "status": e.status,
                "installed_path": e.installed_path,
                "file_exists": e.file_exists,
                "checksum_state": e.checksum_state,
                "problems": e.problems,
            }
            for e in report.entries
        ],
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "safety": {
            "read_only": True,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_verify_rule(report: VerifyRuleReport) -> str:
    lines = ["PipeTune WirePlumber Verify Rule", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *_INTEGRITY_SAFETY_LINES])
    return "\n".join(lines)


def render_verify_rule_json(report: VerifyRuleReport) -> str:
    payload = {
        "command": "wireplumber verify-rule",
        "verdict": report.verdict,
        "passed": report.passed,
        "install_id": report.install_id,
        "rule_id": report.rule_id,
        "status": report.status,
        "installed_path": report.installed_path,
        "file_exists": report.file_exists,
        "checksum_state": report.checksum_state,
        "problems": report.problems,
        "manifest_path": report.manifest_path,
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "safety": {
            "read_only": True,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_repair_report(report: RepairReport) -> str:
    lines = ["PipeTune WirePlumber Repair Rule State (Dry Run)", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.proposed_actions:
        lines.extend(["", "Proposed actions:"])
        lines.extend(f"  {a}" for a in report.proposed_actions)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    lines.extend(["", "Dry run only. No files were modified.", *_INTEGRITY_SAFETY_LINES])
    return "\n".join(lines)


def render_repair_report_json(report: RepairReport) -> str:
    payload = {
        "command": "wireplumber repair-rule-state",
        "dry_run": report.dry_run,
        "verdict": report.verdict,
        "manifest_path": report.manifest_path,
        "proposed_actions": report.proposed_actions,
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


def render_cleanup_report(report: CleanupReport) -> str:
    mode = "Dry Run" if report.dry_run else "Cleanup"
    lines = [f"PipeTune WirePlumber Cleanup Rolled-Back Rules ({mode})", ""]
    lines.extend(f"- {c}" for c in report.checks)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {w}" for w in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {e}" for e in report.errors)
    if not report.dry_run:
        lines.append(f"\nRemoved {report.removed_count} manifest entries.")
    lines.extend(["", f"Final verdict: {report.verdict}", *_INTEGRITY_SAFETY_LINES])
    return "\n".join(lines)


def render_cleanup_report_json(report: CleanupReport) -> str:
    payload = {
        "command": "wireplumber cleanup-rolled-back-rules",
        "dry_run": report.dry_run,
        "verdict": report.verdict,
        "passed": report.passed,
        "removed_count": report.removed_count,
        "planned_count": report.planned_count,
        "manifest_path": report.manifest_path,
        "checks": report.checks,
        "warnings": report.warnings,
        "errors": report.errors,
        "safety": {
            "read_only": report.dry_run,
            "restarted_services": False,
            "changed_routing": False,
            "modified_system": False,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)
