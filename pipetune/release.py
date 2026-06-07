"""Release quality gate checks for PipeTune Linux."""

from __future__ import annotations

import json
import re
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
from pipetune.profiles.validator import ProfileDbReport, run_profile_db_validation

_CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"
_BARE_SORD_PATTERN = re.compile(r"apt.get install[^#\n]*\bsord\b(?!-validate)")

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
    artifact_report = run_package_artifact_check()
    _merge_sub_report("package artifact-check", artifact_report, checks, warnings, errors)
    if artifact_report.verdict == "warn" and _only_removable_artifact_warnings(artifact_report.warnings):
        warnings.append(
            "removable local development artifacts detected; "
            "run: pipetune package clean-local then re-run release check"
        )

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

    _merge_profile_db_report(run_profile_db_validation(), checks, warnings, errors)

    _check_ci_no_bare_sord(checks, errors)
    _check_wireplumber_install_safety(checks, errors)

    return ReleaseCheckReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def _check_ci_no_bare_sord(checks: list[str], errors: list[str]) -> None:
    """Fail release check if CI workflow installs the non-existent bare 'sord' package."""
    if not _CI_WORKFLOW_PATH.exists():
        errors.append("CI workflow .github/workflows/ci.yml not found")
        return
    content = _CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    if _BARE_SORD_PATTERN.search(content):
        errors.append(
            "CI workflow installs bare 'sord' package which does not exist on Ubuntu noble; "
            "remove it and use 'sord-validate || true' instead"
        )
    else:
        checks.append("CI workflow: no bare sord package install")


def _check_wireplumber_install_safety(checks: list[str], errors: list[str]) -> None:
    """Fail release check if WirePlumber install-preflight or install-guide modules are missing."""
    try:
        from pipetune.wireplumber import preflight as _pf  # noqa: F401
        from pipetune.wireplumber import guide as _g  # noqa: F401
        checks.append("WirePlumber install safety commands: install-preflight and install-guide available")
    except ImportError as exc:
        errors.append(f"WirePlumber install safety commands missing: {exc}")


def _merge_profile_db_report(
    report: ProfileDbReport,
    checks: list[str],
    warnings: list[str],
    errors: list[str],
) -> None:
    if report.verdict == "pass":
        checks.append("profile database validation: pass")
    elif report.verdict == "warn":
        warnings.append("profile database validation: warn — " + "; ".join(report.warnings))
    else:
        errors.append("profile database validation: fail — " + "; ".join(report.errors))


_REMOVABLE_ARTIFACT_KEYWORDS = ("egg-info", "clean-local")


def _only_removable_artifact_warnings(warnings: list[str]) -> bool:
    return bool(warnings) and all(
        any(keyword in w for keyword in _REMOVABLE_ARTIFACT_KEYWORDS)
        for w in warnings
    )


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
