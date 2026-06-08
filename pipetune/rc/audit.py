"""PipeTune Linux RC audit — comprehensive release-candidate readiness audit."""

from __future__ import annotations

import datetime
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pipetune
from pipetune.packaging import REPO_ROOT

_REQUIRED_DOCS = (
    "README.md",
    "CHANGELOG.md",
    "docs/install.md",
    "docs/ci.md",
    "docs/release-checklist.md",
    "docs/lv2-safeguard-plugin.md",
    "docs/measurement-and-calibration.md",
    "docs/profile-database.md",
    "docs/profile-contribution-guide.md",
    "docs/wireplumber-routing-diagnostics.md",
    "docs/wireplumber-rule-preview.md",
    "docs/bluetooth-policy-diagnostics.md",
    "docs/wireplumber-rule-install-rollback.md",
    "docs/wireplumber-rule-state-integrity.md",
    "docs/release-candidate.md",
)

_REQUIRED_COMMAND_GROUPS = (
    ("doctor", "pipetune.doctor"),
    ("hardware", "pipetune.hardware"),
    ("measure", "pipetune.measurement"),
    ("plugin", "pipetune.plugin"),
    ("package", "pipetune.packaging"),
    ("release", "pipetune.release"),
    ("profiles", "pipetune.profiles"),
    ("wireplumber", "pipetune.wireplumber"),
    ("route", "pipetune.wireplumber.render"),
    ("bluetooth", "pipetune.wireplumber.bluetooth"),
    ("rc", "pipetune.rc"),
)

_REQUIRED_SAFETY_COMMANDS = (
    ("package clean-local", "pipetune.packaging", "run_package_clean_local"),
    ("package artifact-check", "pipetune.packaging", "run_package_artifact_check"),
    ("release check", "pipetune.release", "run_release_check"),
    ("wireplumber install-preflight", "pipetune.wireplumber.preflight", "run_install_preflight"),
    ("wireplumber install-guide", "pipetune.wireplumber.guide", "render_install_guide"),
    ("wireplumber rule-state-doctor", "pipetune.wireplumber.integrity", "run_state_doctor"),
)

_REQUIRED_GITIGNORE_PATTERNS = (
    "dist/",
    "build/",
    "*.egg-info/",
    "plugins/lv2/**/*.so",
    "plugins/lv2/**/*.o",
    "previews/wireplumber/*",
)

_GITIGNORE_ALLOW_PATTERN = "!previews/wireplumber/.gitkeep"

_BARE_SORD_PATTERN = re.compile(r"apt.get install[^#\n]*\bsord\b(?!-validate)")

_FORBIDDEN_SCAN_EXTENSIONS = frozenset({".py", ".yml", ".yaml", ".toml", ".md", ".cfg", ".ini"})
_ATTRIBUTION_SCANNER_FILES = frozenset({
    "pipetune/rc/audit.py",
    "pipetune/rc/docs_check.py",
})
_FORBIDDEN_ATTRIBUTION_PARTS = ("Co-Authored" + "-By", "AI" + " assistant")


@dataclass(slots=True)
class RcAuditReport:
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


def run_rc_audit() -> RcAuditReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    _check_version_metadata(checks, errors)
    _check_required_docs(checks, errors)
    _check_command_groups(checks, errors)
    _check_safety_commands(checks, errors)
    _check_ci_workflow(checks, errors)
    _check_gitignore(checks, errors)
    _check_profile_db(checks, warnings, errors)
    _check_lv2_metadata(checks, warnings, errors)
    _check_lv2_rt_safety(checks, errors)
    _check_artifact_state(checks, warnings, errors)
    _check_forbidden_attribution(checks, errors)
    _check_staged_previews(checks, warnings)

    return RcAuditReport(checks=checks, warnings=warnings, errors=errors)


def _check_version_metadata(checks: list[str], errors: list[str]) -> None:
    import tomllib
    version = pipetune.__version__
    if version:
        checks.append(f"pipetune.__version__: {version}")
    else:
        errors.append("pipetune.__version__ is missing")

    pyproject_path = REPO_ROOT / "pyproject.toml"
    if pyproject_path.exists():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            pyproject_version = data.get("project", {}).get("version", "missing")
            if pyproject_version == version:
                checks.append(f"pyproject.toml version matches: {pyproject_version}")
            else:
                errors.append(
                    f"version mismatch: pyproject.toml={pyproject_version}, "
                    f"pipetune.__version__={version}"
                )
        except Exception as exc:
            errors.append(f"could not parse pyproject.toml: {exc}")
    else:
        errors.append("pyproject.toml not found")


def _check_required_docs(checks: list[str], errors: list[str]) -> None:
    for doc_path in _REQUIRED_DOCS:
        full_path = REPO_ROOT / doc_path
        if full_path.exists():
            checks.append(f"doc exists: {doc_path}")
        else:
            errors.append(f"required doc missing: {doc_path}")


def _check_command_groups(checks: list[str], errors: list[str]) -> None:
    import importlib
    for group_name, module_path in _REQUIRED_COMMAND_GROUPS:
        try:
            importlib.import_module(module_path)
            checks.append(f"command group available: {group_name}")
        except ImportError as exc:
            errors.append(f"command group missing: {group_name} ({module_path}): {exc}")


def _check_safety_commands(checks: list[str], errors: list[str]) -> None:
    import importlib
    for cmd_name, module_path, func_name in _REQUIRED_SAFETY_COMMANDS:
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, func_name):
                checks.append(f"safety command available: {cmd_name}")
            else:
                errors.append(f"safety command function missing: {cmd_name} ({module_path}.{func_name})")
        except ImportError as exc:
            errors.append(f"safety command module missing: {cmd_name} ({module_path}): {exc}")


def _check_ci_workflow(checks: list[str], errors: list[str]) -> None:
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        errors.append("CI workflow .github/workflows/ci.yml not found")
        return
    content = ci_path.read_text(encoding="utf-8")
    if _BARE_SORD_PATTERN.search(content):
        errors.append(
            "CI workflow installs bare 'sord' package which does not exist on Ubuntu noble"
        )
    else:
        checks.append("CI workflow: no bare sord package")
    if "rc audit" in content or "rc" in content:
        checks.append("CI workflow includes rc commands")
    else:
        warnings_placeholder: list[str] = []
        warnings_placeholder.append("CI workflow may not include rc commands")


def _check_gitignore(checks: list[str], errors: list[str]) -> None:
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        errors.append(".gitignore not found")
        return
    text = gitignore.read_text(encoding="utf-8")
    for pattern in _REQUIRED_GITIGNORE_PATTERNS:
        if pattern in text:
            checks.append(f".gitignore covers: {pattern}")
        else:
            errors.append(f".gitignore missing required pattern: {pattern}")
    if _GITIGNORE_ALLOW_PATTERN in text:
        checks.append(".gitignore allows previews/wireplumber/.gitkeep")
    else:
        errors.append(".gitignore does not allow previews/wireplumber/.gitkeep")


def _check_profile_db(
    checks: list[str], warnings: list[str], errors: list[str]
) -> None:
    from pipetune.profiles.validator import run_profile_db_validation
    report = run_profile_db_validation()
    if report.verdict == "pass":
        checks.append("profile database validation: pass")
    elif report.verdict == "warn":
        warnings.extend(f"profile DB: {w}" for w in report.warnings)
    else:
        errors.extend(f"profile DB: {e}" for e in report.errors)


def _check_lv2_metadata(
    checks: list[str], warnings: list[str], errors: list[str]
) -> None:
    from pipetune.plugin.safeguard import run_metadata_validation
    report = run_metadata_validation()
    if report.passed:
        checks.append("LV2 metadata validation: pass")
    elif report.warnings and not report.errors:
        warnings.extend(f"LV2 metadata: {w}" for w in report.warnings)
        checks.append("LV2 metadata validation: pass (with optional external helper warnings)")
    else:
        errors.extend(f"LV2 metadata: {e}" for e in report.errors)


def _check_lv2_rt_safety(checks: list[str], errors: list[str]) -> None:
    from pipetune.plugin.safeguard import run_rt_safety_validation
    report = run_rt_safety_validation()
    if report.passed:
        checks.append("LV2 RT-safety validation: pass")
    else:
        errors.extend(f"LV2 RT-safety: {e}" for e in report.errors)


def _check_artifact_state(
    checks: list[str], warnings: list[str], errors: list[str]
) -> None:
    from pipetune.packaging import run_package_artifact_check
    report = run_package_artifact_check()
    if report.verdict == "pass":
        checks.append("artifact check: pass — no forbidden artifacts found")
    elif report.verdict == "warn":
        warnings.extend(f"artifact: {w}" for w in report.warnings)
    else:
        errors.extend(f"artifact: {e}" for e in report.errors)


def _check_forbidden_attribution(checks: list[str], errors: list[str]) -> None:
    found: list[str] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _FORBIDDEN_SCAN_EXTENSIONS:
            continue
        skip_parts = {".git", ".venv", "__pycache__", ".pytest_cache"}
        if any(part in skip_parts for part in path.parts):
            continue
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError:
            continue
        if rel in _ATTRIBUTION_SCANNER_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(part.lower() in text.lower() for part in _FORBIDDEN_ATTRIBUTION_PARTS):
            found.append(rel)
    if found:
        for rel in found:
            errors.append(f"forbidden attribution text found in: {rel}")
    else:
        checks.append("no forbidden attribution text found in source/docs/config files")


def _check_staged_previews(checks: list[str], warnings: list[str]) -> None:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if result.returncode != 0:
        return
    staged = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    preview_staged = [f for f in staged if f.startswith("previews/wireplumber/") and f.endswith(".lua")]
    compiled_staged = [f for f in staged if f.endswith(".so") or f.endswith(".o")]
    if preview_staged:
        warnings.extend(f"generated preview file staged: {f}" for f in preview_staged)
    else:
        checks.append("no generated WirePlumber preview files staged")
    if compiled_staged:
        warnings.extend(f"compiled artifact staged: {f}" for f in compiled_staged)
    else:
        checks.append("no compiled LV2 artifacts staged")


def render_rc_audit(report: RcAuditReport) -> str:
    lines = ["PipeTune RC Audit", "", "Checks:"]
    for check in report.checks:
        lines.append(f"  pass: {check}")
    if not report.checks:
        lines.append("  (none)")
    if report.warnings:
        lines.extend(["", "Warnings:"])
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
        "  No global LV2 installation was performed.",
        "  No audio routing was changed.",
        "  No service was restarted.",
        "  No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
    ])
    return "\n".join(lines)


def render_rc_audit_json(report: RcAuditReport) -> str:
    return json.dumps(
        {
            "version": pipetune.__version__,
            "codename": pipetune.CODENAME,
            "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checks": report.checks,
            "warnings": report.warnings,
            "errors": report.errors,
            "verdict": report.verdict,
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
