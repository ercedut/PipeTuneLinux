"""Release quality gate checks for PipeTune Linux."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pipetune
from pipetune.packaging import (
    PACKAGE_SAFETY_DISCLAIMER,
    REPO_ROOT,
    PackageReport,
    run_package_artifact_check,
    run_package_build_check,
    run_package_inspect,
    run_package_smoke_test,
)
from pipetune.plugin.safeguard import run_metadata_validation, run_rt_safety_validation

REQUIRED_FILES = (
    "README.md",
    "CHANGELOG.md",
    "MANIFEST.in",
    "pyproject.toml",
    "docs/install.md",
    "docs/release-checklist.md",
)


@dataclass(slots=True)
class ReleaseCheckReport:
    passed: bool
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


def run_release_check() -> ReleaseCheckReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    if pipetune.__version__:
        checks.append(f"version metadata: {pipetune.__version__}")
    else:
        errors.append("version metadata missing from pipetune.__version__")

    for required_file in REQUIRED_FILES:
        if (REPO_ROOT / required_file).exists():
            checks.append(f"required file exists: {required_file}")
        else:
            errors.append(f"required file missing: {required_file}")

    _merge_sub_report("package inspect", run_package_inspect(), checks, warnings, errors)
    _merge_sub_report("package build-check", run_package_build_check(), checks, warnings, errors)
    _merge_sub_report("package smoke-test", run_package_smoke_test(), checks, warnings, errors)
    _merge_sub_report("package artifact-check", run_package_artifact_check(), checks, warnings, errors)

    metadata_report = run_metadata_validation()
    if metadata_report.passed:
        checks.append("plugin metadata validation: pass")
    else:
        errors.append("plugin metadata validation: fail — " + "; ".join(metadata_report.errors))

    rt_report = run_rt_safety_validation()
    if rt_report.passed:
        checks.append("plugin RT-safety validation: pass")
    else:
        errors.append("plugin RT-safety validation: fail — " + "; ".join(rt_report.errors))

    return ReleaseCheckReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def _merge_sub_report(
    label: str,
    report: PackageReport,
    checks: list[str],
    warnings: list[str],
    errors: list[str],
) -> None:
    if report.verdict == "pass":
        checks.append(f"{label}: pass")
    elif report.verdict == "warn":
        warnings.append(f"{label}: warn — " + "; ".join(report.warnings))
    else:
        errors.append(f"{label}: fail — " + "; ".join(report.errors))


def render_release_check_report(report: ReleaseCheckReport) -> str:
    lines = ["PipeTune Release Check", "", "Checks:"]
    if report.checks:
        lines.extend(f"- pass: {check}" for check in report.checks)
    else:
        lines.append("- none")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {warning}" for warning in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {error}" for error in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *PACKAGE_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def render_release_check_json(report: ReleaseCheckReport) -> str:
    return json.dumps(
        {
            "version": pipetune.__version__,
            "verdict": report.verdict,
            "passed": report.passed,
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
        },
        indent=2,
    )
