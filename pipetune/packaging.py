"""Packaging and release-readiness checks for PipeTune Linux."""

from __future__ import annotations

import fnmatch
import importlib.metadata
import importlib.util
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pipetune

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PACKAGE_NAME = "pipetune-linux"
CLI_ENTRY_POINT = "pipetune"
PLUGIN_SOURCE_DIR = REPO_ROOT / "plugins" / "lv2" / "pipetune-safeguard.lv2"
PACKAGE_SAFETY_DISCLAIMER = [
    "No package was uploaded.",
    "No global LV2 installation was performed.",
    "No audio routing was changed.",
    "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified.",
]
REQUIRED_PROJECT_FIELDS = (
    "name",
    "version",
    "description",
    "authors",
    "license",
    "readme",
    "requires-python",
    "dependencies",
)
REQUIRED_PLUGIN_SOURCES = (
    "manifest.ttl",
    "pipetune-safeguard.ttl",
    "pipetune_safeguard.c",
    "Makefile",
)
LOCAL_FORBIDDEN_ARTIFACT_PATTERNS = (
    "plugins/lv2/**/*.so",
    "plugins/lv2/**/*.o",
    "plugins/lv2/**/*.d",
    "plugins/lv2/**/*.tmp",
)
ARCHIVE_FORBIDDEN_PATTERNS = (
    "*.so",
    "*.o",
    "*.d",
    "*.tmp",
    "*/.venv/*",
    "*/__pycache__/*",
    "*/.pytest_cache/*",
    "*/dist/*",
    "*/build/*",
    "*/measurements/*",
    "*/generated/*",
    "*/verification/microphone/*",
)


@dataclass(slots=True)
class PackageReport:
    passed: bool
    checks: list[str]
    warnings: list[str]
    errors: list[str]

    @property
    def verdict(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"


def run_package_inspect() -> PackageReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    pyproject = _read_pyproject(errors)
    project = pyproject.get("project", {}) if pyproject else {}

    package_name = project.get("name", "missing")
    version = project.get("version", "missing")
    if package_name == PACKAGE_NAME:
        checks.append(f"package name: {package_name}")
    else:
        errors.append(f"package name mismatch: expected {PACKAGE_NAME}, found {package_name}")

    if version == pipetune.__version__:
        checks.append(f"project version: {version}")
    else:
        errors.append(f"version mismatch: pyproject={version}, package={pipetune.__version__}")

    checks.append(f"Python executable: {sys.executable}")
    checks.append(f"package root: {Path(pipetune.__file__).resolve().parent}")

    scripts = project.get("scripts", {})
    if scripts.get(CLI_ENTRY_POINT) == "pipetune.cli:main":
        checks.append("CLI entry point configured: yes")
    else:
        errors.append("CLI entry point is missing or does not point to pipetune.cli:main.")

    if _entry_point_installed():
        checks.append("CLI entry point installed: yes")
    else:
        warnings.append("CLI entry point installed: no; run pip install -e . before installed-command verification.")

    if _plugin_sources_present():
        checks.append("plugin source bundle present: yes")
    else:
        errors.append("plugin source bundle present: no")

    compiled_artifacts = _compiled_plugin_artifacts()
    if compiled_artifacts:
        warnings.append("compiled plugin artifacts present: yes (" + ", ".join(str(path) for path in compiled_artifacts) + ")")
    else:
        checks.append("compiled plugin artifacts present: no")

    if (REPO_ROOT / "docs").is_dir() and any((REPO_ROOT / "docs").glob("*.md")):
        checks.append("docs present: yes")
    else:
        errors.append("docs present: no")

    if (REPO_ROOT / "tests").is_dir() and any((REPO_ROOT / "tests").glob("test_*.py")):
        checks.append("tests present: yes")
    else:
        errors.append("tests present: no")

    return PackageReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def run_package_build_check() -> PackageReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    pyproject = _read_pyproject(errors)
    project = pyproject.get("project", {}) if pyproject else {}

    _check_required_file("pyproject.toml", checks, errors)
    _check_required_file("README.md", checks, errors)
    _check_required_file("LICENSE", checks, errors)
    _check_required_file("CHANGELOG.md", checks, errors)
    _check_required_file("MANIFEST.in", checks, errors)

    for field in REQUIRED_PROJECT_FIELDS:
        if field in project:
            checks.append(f"pyproject field present: {field}")
        else:
            errors.append(f"pyproject field missing: {field}")

    scripts = project.get("scripts", {})
    if scripts.get(CLI_ENTRY_POINT) == "pipetune.cli:main":
        checks.append("console script entry point present")
    else:
        errors.append("console script entry point missing or incorrect.")

    if project.get("dependencies") == []:
        checks.append("runtime dependencies are explicit and empty")
    else:
        warnings.append("runtime dependencies are present; verify they are intentional.")

    if _plugin_sources_present():
        checks.append("LV2 source bundle is available for source distribution")
    else:
        errors.append("LV2 source bundle is incomplete.")

    forbidden_artifacts = _local_forbidden_artifacts()
    if forbidden_artifacts:
        errors.append("Forbidden local artifacts detected: " + ", ".join(str(path) for path in forbidden_artifacts))
    else:
        checks.append("no compiled LV2 or temporary plugin artifacts found in source tree")

    _check_gitignore_patterns(checks, errors)

    if importlib.util.find_spec("build") is None:
        warnings.append("python build module is not installed; install with: python -m pip install build")
    else:
        build_checks, build_warnings, build_errors = _attempt_local_build()
        checks.extend(build_checks)
        warnings.extend(build_warnings)
        errors.extend(build_errors)

    return PackageReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def run_package_smoke_test() -> PackageReport:
    return run_package_smoke_test_with_runner(_run_cli_command)


def run_package_smoke_test_with_runner(runner) -> PackageReport:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []

    smoke_commands = [
        ("pipetune version", ["version"]),
        ("pipetune doctor", ["doctor"]),
        ("pipetune profile state-doctor", ["profile", "state-doctor"]),
        ("pipetune plugin info", ["plugin", "info"]),
        ("pipetune plugin validate --metadata", ["plugin", "validate", "--metadata"]),
    ]
    fixture = REPO_ROOT / "tests" / "fixtures" / "measurement" / "flat.csv"
    if fixture.exists():
        smoke_commands.insert(
            3,
            (
                "pipetune measure validate-response fixture",
                ["measure", "validate-response", "--input", str(fixture)],
            ),
        )
    else:
        warnings.append("measurement response fixture is missing; skipped validate-response smoke check.")

    for label, args in smoke_commands:
        result = runner(args)
        if result.returncode == 0:
            checks.append(f"{label}: pass")
        else:
            errors.append(f"{label}: failed with exit {result.returncode}\n{_compact_output(result.stdout, result.stderr)}")

    checks.append("smoke-test commands are non-mutating checks only")
    return PackageReport(passed=not errors, checks=checks, warnings=warnings, errors=errors)


def render_package_report(title: str, report: PackageReport) -> str:
    lines = [title, "", "Checks:"]
    lines.extend(f"- pass: {check}" for check in report.checks) if report.checks else lines.append("- none")
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- warn: {warning}" for warning in report.warnings)
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- fail: {error}" for error in report.errors)
    lines.extend(["", f"Final verdict: {report.verdict}", *PACKAGE_SAFETY_DISCLAIMER])
    return "\n".join(lines)


def _read_pyproject(errors: list[str]) -> dict:
    if not PYPROJECT_PATH.exists():
        errors.append(f"Missing pyproject.toml: {PYPROJECT_PATH}")
        return {}
    try:
        return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"Could not parse pyproject.toml: {exc}")
        return {}


def _check_required_file(relative_path: str, checks: list[str], errors: list[str]) -> None:
    path = REPO_ROOT / relative_path
    if path.exists():
        checks.append(f"{relative_path} exists")
    else:
        errors.append(f"{relative_path} is missing")


def _entry_point_installed() -> bool:
    try:
        entry_points = importlib.metadata.entry_points()
        scripts = entry_points.select(group="console_scripts")
    except Exception:
        return False
    return any(entry_point.name == CLI_ENTRY_POINT and entry_point.value == "pipetune.cli:main" for entry_point in scripts)


def _plugin_sources_present() -> bool:
    return all((PLUGIN_SOURCE_DIR / source_name).exists() for source_name in REQUIRED_PLUGIN_SOURCES)


def _compiled_plugin_artifacts() -> list[Path]:
    artifacts = list(PLUGIN_SOURCE_DIR.glob("*.so")) + list(PLUGIN_SOURCE_DIR.glob("*.o"))
    return sorted(path for path in artifacts if path.is_file())


def _local_forbidden_artifacts() -> list[Path]:
    artifacts: list[Path] = []
    for pattern in LOCAL_FORBIDDEN_ARTIFACT_PATTERNS:
        artifacts.extend(path for path in REPO_ROOT.glob(pattern) if path.is_file())
    return sorted(set(artifacts))


def _check_gitignore_patterns(checks: list[str], errors: list[str]) -> None:
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        errors.append(".gitignore is missing")
        return
    text = gitignore.read_text(encoding="utf-8")
    required_patterns = (
        ".venv/",
        "**/__pycache__/",
        ".pytest_cache/",
        "dist/",
        "build/",
        "*.egg-info/",
        "plugins/lv2/**/*.so",
        "plugins/lv2/**/*.o",
    )
    for pattern in required_patterns:
        if pattern in text:
            checks.append(f"gitignore covers: {pattern}")
        else:
            errors.append(f".gitignore does not cover required pattern: {pattern}")


def _attempt_local_build() -> tuple[list[str], list[str], list[str]]:
    checks: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    dist_dir = REPO_ROOT / "dist"

    result = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist_dir)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    if result.returncode != 0:
        errors.append("python -m build --no-isolation failed:\n" + result.stdout.strip())
        return checks, warnings, errors

    checks.append("python -m build --no-isolation completed locally")
    archives = sorted(list(dist_dir.glob("*.tar.gz")) + list(dist_dir.glob("*.whl")))
    if not archives:
        errors.append("build completed but no source or wheel archive was found in dist/")
        return checks, warnings, errors

    for archive in archives:
        forbidden = _archive_forbidden_members(archive)
        if forbidden:
            errors.append(f"forbidden artifacts found in {archive}: " + ", ".join(forbidden))
        else:
            checks.append(f"archive excludes forbidden artifacts: {archive.name}")
    return checks, warnings, errors


def _archive_forbidden_members(archive: Path) -> list[str]:
    names: list[str]
    if archive.suffix == ".whl" or archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zip_file:
            names = zip_file.namelist()
    elif archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tar_file:
            names = tar_file.getnames()
    else:
        return [archive.name]

    forbidden: list[str] = []
    for name in names:
        normalized = name.replace("\\", "/")
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in ARCHIVE_FORBIDDEN_PATTERNS):
            forbidden.append(normalized)
    return forbidden


def _run_cli_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pipetune", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
    )


def _compact_output(stdout: str, stderr: str) -> str:
    output = (stdout + "\n" + stderr).strip()
    if not output:
        return "(no output)"
    lines = output.splitlines()
    return "\n".join(lines[:12])


def build_archive_forbidden_check_fixture(names: list[str]) -> list[str]:
    """Test helper for archive exclusion patterns."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive = Path(tmp_dir) / "fixture.whl"
        with zipfile.ZipFile(archive, "w") as zip_file:
            for name in names:
                zip_file.writestr(name, "")
        return _archive_forbidden_members(archive)
