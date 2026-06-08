"""PipeTune Linux RC mutation audit — static source scan for dangerous mutation patterns."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pipetune.packaging import REPO_ROOT

_SUBPROCESS_CMD = r"subprocess\.\w+"
_OSSYSTEM = r"os\.system"

_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # Actual service restart calls (subprocess or os.system)
    (rf"(?:{_SUBPROCESS_CMD}|{_OSSYSTEM}).*systemctl.*restart", "subprocess/os.system: systemctl restart call"),
    (rf"(?:{_SUBPROCESS_CMD}|{_OSSYSTEM}).*systemctl.*--user.*restart", "subprocess/os.system: systemctl --user restart"),
    # Routing mutations via subprocess
    (rf"{_SUBPROCESS_CMD}.*wpctl.*set-default", "subprocess: wpctl set-default (routing change)"),
    (rf"{_SUBPROCESS_CMD}.*pactl.*set-card-profile", "subprocess: pactl set-card-profile (profile mutation)"),
    (rf"{_SUBPROCESS_CMD}.*pactl.*set-default-sink", "subprocess: pactl set-default-sink (routing change)"),
    (rf"{_SUBPROCESS_CMD}.*pactl.*set-default-source", "subprocess: pactl set-default-source (routing change)"),
    (rf"{_SUBPROCESS_CMD}.*bluetoothctl", "subprocess: bluetoothctl call"),
    # Actual sudo elevation via subprocess
    (rf'{_SUBPROCESS_CMD}.*["\']sudo["\']', "subprocess: sudo execution"),
    (rf"{_OSSYSTEM}.*\bsudo\b", "os.system: sudo execution"),
    # Write operations to system paths (actual file writes, not reads)
    (r"write_text\s*\(.*(?:/etc/|/usr/|/lib/|/sys/)", "write_text to system path"),
    (r"write_bytes\s*\(.*(?:/etc/|/usr/|/lib/|/sys/)", "write_bytes to system path"),
    (r"open\s*\([^)]*(?:/etc/|/usr/|/lib/|/sys/)[^)]*[\"']\s*,\s*[\"']w", "open-write to system path"),
    # Write to real wireplumber config (non-XDG, outside test isolation)
    (r"write_text\s*\(.*home.*\.config.wireplumber", "write_text to ~/.config/wireplumber (non-XDG)"),
    (r"write_bytes\s*\(.*home.*\.config.wireplumber", "write_bytes to ~/.config/wireplumber (non-XDG)"),
]

_COMPILED_PATTERNS = [(re.compile(pat, re.IGNORECASE), desc) for pat, desc in _DANGEROUS_PATTERNS]

_SELF_EXCLUDE = frozenset({"pipetune/rc/mutation_audit.py"})


@dataclass(slots=True)
class MutationFinding:
    file: str
    line_number: int
    line_text: str
    pattern_description: str
    severity: str


@dataclass(slots=True)
class MutationAuditReport:
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    findings: list[MutationFinding] = field(default_factory=list)

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


def _classify_file(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return "unknown"
    parts = rel.parts
    if parts and parts[0] == "tests":
        return "test"
    if parts and parts[0] == "docs":
        return "docs"
    if parts and parts[0] == "pipetune":
        return "production"
    if parts and parts[0] in (".github",):
        return "ci"
    return "other"


def _scan_file(path: Path, root: Path, findings: list[MutationFinding]) -> None:
    try:
        rel_str = str(path.relative_to(root))
    except ValueError:
        rel_str = str(path)
    if rel_str in _SELF_EXCLUDE:
        return
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    file_type = _classify_file(path, root)
    for line_num, line in enumerate(content.splitlines(), 1):
        for compiled_pattern, description in _COMPILED_PATTERNS:
            if compiled_pattern.search(line):
                severity = "error" if file_type == "production" else "warn"
                findings.append(MutationFinding(
                    file=rel_str,
                    line_number=line_num,
                    line_text=line.strip()[:120],
                    pattern_description=description,
                    severity=severity,
                ))


def run_mutation_audit(root: Path = REPO_ROOT) -> MutationAuditReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    findings: list[MutationFinding] = []

    py_dirs = [root / "pipetune", root / "tests"]
    doc_dirs = [root / "docs"]

    scanned_count = 0
    for py_dir in py_dirs:
        if py_dir.is_dir():
            for py_file in sorted(py_dir.rglob("*.py")):
                if ".venv" in py_file.parts or "__pycache__" in py_file.parts:
                    continue
                _scan_file(py_file, root, findings)
                scanned_count += 1

    for doc_dir in doc_dirs:
        if doc_dir.is_dir():
            for md_file in sorted(doc_dir.rglob("*.md")):
                _scan_file(md_file, root, findings)
                scanned_count += 1

    checks.append(f"scanned {scanned_count} source and doc files")

    error_findings = [f for f in findings if f.severity == "error"]
    warn_findings = [f for f in findings if f.severity == "warn"]

    if error_findings:
        for finding in error_findings:
            errors.append(
                f"DANGEROUS pattern in production source "
                f"{finding.file}:{finding.line_number}: {finding.pattern_description}"
            )
    else:
        checks.append("no dangerous mutation patterns found in production source")

    if warn_findings:
        for finding in warn_findings:
            warnings.append(
                f"mutation pattern reference in {finding.file}:{finding.line_number}: "
                f"{finding.pattern_description} (docs/test context — verify intentional)"
            )

    if not findings:
        checks.append("mutation audit: clean — no dangerous patterns detected")

    return MutationAuditReport(
        checks=checks,
        warnings=warnings,
        errors=errors,
        findings=findings,
    )


def render_mutation_audit(report: MutationAuditReport) -> str:
    lines = ["PipeTune RC Mutation Audit", ""]
    lines.append("Checks:")
    for check in report.checks:
        lines.append(f"- pass: {check}")
    if report.warnings:
        lines.extend(["", "Warnings (docs/test context):"])
        for warning in report.warnings:
            lines.append(f"- warn: {warning}")
    if report.errors:
        lines.extend(["", "Errors (dangerous production code):"])
        for error in report.errors:
            lines.append(f"- fail: {error}")
    lines.extend([
        "",
        f"Verdict: {report.verdict}",
        "",
        "No system configuration was modified.",
        "No audio routing was changed.",
    ])
    return "\n".join(lines)


def render_mutation_audit_json(report: MutationAuditReport) -> str:
    return json.dumps(
        {
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "finding_count": len(report.findings),
            "findings": [
                {
                    "file": f.file,
                    "line_number": f.line_number,
                    "pattern_description": f.pattern_description,
                    "severity": f.severity,
                }
                for f in report.findings
            ],
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
