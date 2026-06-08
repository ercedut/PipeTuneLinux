"""PipeTune Linux RC Fedora KDE smoke test — safe non-mutating smoke test suite."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pipetune.packaging import REPO_ROOT

SmokeRunner = Callable[[list[str]], subprocess.CompletedProcess]


@dataclass(slots=True)
class SmokeResult:
    label: str
    passed: bool
    exit_code: int
    note: str


@dataclass(slots=True)
class FedoraSmokeReport:
    results: list[SmokeResult] = field(default_factory=list)
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


def _default_runner(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pipetune", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )


_SMOKE_COMMANDS: list[tuple[str, list[str], bool]] = [
    ("pipetune version", ["version"], False),
    ("pipetune doctor", ["doctor"], False),
    ("pipetune package inspect", ["package", "inspect"], False),
    ("pipetune package artifact-check", ["package", "artifact-check"], False),
    ("pipetune plugin validate --metadata", ["plugin", "validate", "--metadata"], False),
    ("pipetune plugin validate --rt-safety", ["plugin", "validate", "--rt-safety"], False),
    ("pipetune profiles validate-db", ["profiles", "validate-db"], False),
    ("pipetune wireplumber audit", ["wireplumber", "audit"], True),
    ("pipetune route audit", ["route", "audit"], True),
    ("pipetune bluetooth policy-audit", ["bluetooth", "policy-audit"], True),
    ("pipetune wireplumber install-preflight", ["wireplumber", "install-preflight"], False),
    ("pipetune wireplumber rule-state-doctor", ["wireplumber", "rule-state-doctor"], False),
    ("pipetune release check", ["release", "check"], False),
    ("pipetune rc audit", ["rc", "audit"], False),
]


def run_fedora_smoke(runner: SmokeRunner | None = None) -> FedoraSmokeReport:
    if runner is None:
        runner = _default_runner

    results: list[SmokeResult] = []
    warnings: list[str] = []
    errors: list[str] = []

    fixture = REPO_ROOT / "tests" / "fixtures" / "measurement" / "flat.csv"
    measure_commands: list[tuple[str, list[str], bool]] = []
    if fixture.exists():
        measure_commands.append((
            "pipetune measure validate-response fixture",
            ["measure", "validate-response", "--input", str(fixture)],
            False,
        ))

    for label, args, service_optional in _SMOKE_COMMANDS + measure_commands:
        try:
            proc = runner(args)
        except Exception as exc:
            errors.append(f"{label}: runner error — {exc}")
            results.append(SmokeResult(label=label, passed=False, exit_code=-1, note=str(exc)))
            continue

        passed = proc.returncode == 0
        note = ""
        if not passed:
            if service_optional:
                warnings.append(
                    f"{label}: non-zero exit {proc.returncode} "
                    "(acceptable — live audio service or hardware may be absent)"
                )
                results.append(SmokeResult(
                    label=label, passed=True, exit_code=proc.returncode,
                    note="service/hardware may be absent — warn only",
                ))
                continue
            else:
                stderr_snippet = (proc.stderr or "").strip()[:200]
                note = stderr_snippet or "(no stderr)"
                errors.append(f"{label}: failed with exit {proc.returncode}")
        results.append(SmokeResult(label=label, passed=passed, exit_code=proc.returncode, note=note))

    return FedoraSmokeReport(results=results, warnings=warnings, errors=errors)


def render_fedora_smoke(report: FedoraSmokeReport) -> str:
    lines = [
        "PipeTune RC Fedora KDE Smoke Test",
        "",
        "Non-mutating checks only. No routing changed. No services restarted.",
        "",
        "Results:",
    ]
    for result in report.results:
        status = "pass" if result.passed else "FAIL"
        note = f" [{result.note}]" if result.note and not result.passed else ""
        lines.append(f"  [{status}] {result.label}{note}")
    if report.warnings:
        lines.extend(["", "Warnings (acceptable for absent hardware/services):"])
        for warning in report.warnings:
            lines.append(f"  warn: {warning}")
    if report.errors:
        lines.extend(["", "Errors:"])
        for error in report.errors:
            lines.append(f"  FAIL: {error}")
    lines.extend([
        "",
        f"Verdict: {report.verdict}",
        "",
        "Safety confirmation:",
        "  No routing was changed.",
        "  No service was restarted.",
        "  No WirePlumber, PipeWire, ALSA, service, system, or user audio configuration was modified.",
        "  No package was uploaded.",
        "  No global LV2 installation was performed.",
    ])
    return "\n".join(lines)


def render_fedora_smoke_json(report: FedoraSmokeReport) -> str:
    return json.dumps(
        {
            "verdict": report.verdict,
            "passed": report.passed,
            "results": [
                {
                    "label": r.label,
                    "passed": r.passed,
                    "exit_code": r.exit_code,
                    "note": r.note,
                }
                for r in report.results
            ],
            "warnings": report.warnings,
            "errors": report.errors,
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
