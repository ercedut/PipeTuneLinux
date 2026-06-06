"""Tests for v0.6.1 release quality gate and artifact check commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

import pipetune
from pipetune import cli
from pipetune import packaging as pkg
from pipetune import release as rel


# ---------------------------------------------------------------------------
# Artifact check — unit tests
# ---------------------------------------------------------------------------


def test_artifact_check_passes_on_clean_tree(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)

    report = pkg.run_package_artifact_check()
    assert report.verdict in ("pass", "warn")
    assert not report.errors


def test_artifact_check_errors_on_compiled_so(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    plugin_dir = tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "pipetune_safeguard.so").write_text("compiled", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert report.verdict == "fail"
    assert any(".so" in e for e in report.errors)


def test_artifact_check_errors_on_compiled_o(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    plugin_dir = tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "pipetune_safeguard.o").write_text("compiled", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert report.verdict == "fail"
    assert any(".o" in e for e in report.errors)


def test_artifact_check_warns_on_dist_dir(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "some.whl").write_text("wheel", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert any("dist/" in w for w in report.warnings)


def test_artifact_check_warns_on_build_dir(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "artifact").write_text("artifact", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert any("build/" in w for w in report.warnings)


def test_artifact_check_warns_on_egg_info(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    egg_dir = tmp_path / "pipetune_linux.egg-info"
    egg_dir.mkdir()
    (egg_dir / "PKG-INFO").write_text("info", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert any("egg-info" in w for w in report.warnings)


def test_artifact_check_staged_so_is_error(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)

    def fake_staged() -> list[str]:
        return ["forbidden staged artifact (compiled shared object): plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.so"]

    monkeypatch.setattr(pkg, "_check_staged_artifacts", fake_staged)
    report = pkg.run_package_artifact_check()
    assert report.verdict == "fail"
    assert any("staged" in e for e in report.errors)


def test_artifact_check_staged_dist_is_error(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)

    def fake_staged() -> list[str]:
        return ["forbidden staged artifact (distribution artifact): dist/pipetune_linux-0.6.1-py3-none-any.whl"]

    monkeypatch.setattr(pkg, "_check_staged_artifacts", fake_staged)
    report = pkg.run_package_artifact_check()
    assert report.verdict == "fail"


def test_artifact_check_staged_filter_logic() -> None:
    import fnmatch

    patterns = [p for p, _ in pkg.STAGED_FORBIDDEN_PATTERNS]
    assert fnmatch.fnmatch("pipetune_safeguard.so", "*.so")
    assert fnmatch.fnmatch("plugins/lv2/safeguard/lib.so", "*.so")
    assert fnmatch.fnmatch("dist/something.whl", "dist/*")
    assert fnmatch.fnmatch("build/temp/obj.o", "*.o")
    assert fnmatch.fnmatch("pipetune_linux.egg-info/SOURCES.txt", "*.egg-info/*")


# ---------------------------------------------------------------------------
# Artifact check — CLI integration
# ---------------------------------------------------------------------------


def test_artifact_check_cli_exits_zero_when_no_errors(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_artifact_check",
        lambda: pkg.PackageReport(passed=True, checks=["no compiled plugin artifacts (.so, .o) in plugin tree"], warnings=[], errors=[]),
    )
    exit_code = cli.main(["package", "artifact-check"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Package Artifact Check" in output
    assert "Final verdict: pass" in output
    assert "No PipeWire, WirePlumber, ALSA" in output


def test_artifact_check_cli_json_output(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_artifact_check",
        lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=["some warning"], errors=[]),
    )
    exit_code = cli.main(["package", "artifact-check", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["verdict"] == "warn"
    assert data["passed"] is True
    assert "ok" in data["checks"]
    assert "some warning" in data["warnings"]


def test_artifact_check_cli_exits_nonzero_on_fail(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_artifact_check",
        lambda: pkg.PackageReport(
            passed=False,
            checks=[],
            warnings=[],
            errors=["compiled plugin artifacts present: plugins/lv2/p.so"],
        ),
    )
    exit_code = cli.main(["package", "artifact-check"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Final verdict: fail" in output


def test_artifact_check_no_system_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_artifact_check",
        lambda: pkg.PackageReport(passed=True, checks=["clean"], warnings=[], errors=[]),
    )
    cli.main(["package", "artifact-check"])
    output = capsys.readouterr().out
    assert "No package was uploaded." in output
    assert "No global LV2 installation was performed." in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# Release check — unit tests
# ---------------------------------------------------------------------------


def test_release_check_passes_on_real_project() -> None:
    report = rel.run_release_check()
    assert report.verdict in ("pass", "warn")
    assert not report.errors


def test_release_check_errors_on_missing_changelog(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    _patch_repo_root(monkeypatch, tmp_path)
    monkeypatch.setattr(rel, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pkg, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pkg, "PYPROJECT_PATH", tmp_path / "pyproject.toml")
    monkeypatch.setattr(pkg, "PLUGIN_SOURCE_DIR", tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2")
    # Remove CHANGELOG.md to trigger missing file error
    (tmp_path / "CHANGELOG.md").unlink()

    report = rel.run_release_check()
    assert any("CHANGELOG.md" in e for e in report.errors)


def test_release_check_contains_version_metadata() -> None:
    report = rel.run_release_check()
    version_checks = [c for c in report.checks if "version metadata" in c]
    assert version_checks
    assert pipetune.__version__ in version_checks[0]


# ---------------------------------------------------------------------------
# Release check — CLI integration
# ---------------------------------------------------------------------------


def test_release_check_cli_exits_zero_on_pass(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_release_check",
        lambda: rel.ReleaseCheckReport(passed=True, checks=["version metadata: 0.6.1"], warnings=[], errors=[]),
    )
    exit_code = cli.main(["release", "check"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "PipeTune Release Check" in output
    assert "Final verdict: pass" in output


def test_release_check_cli_json_output(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_release_check",
        lambda: rel.ReleaseCheckReport(
            passed=True,
            checks=["version metadata: 0.6.1"],
            warnings=["artifact-check: warn — egg-info found"],
            errors=[],
        ),
    )
    exit_code = cli.main(["release", "check", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    data = json.loads(output)
    assert data["verdict"] == "warn"
    assert data["passed"] is True
    assert data["version"] == pipetune.__version__


def test_release_check_cli_exits_nonzero_on_fail(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_release_check",
        lambda: rel.ReleaseCheckReport(
            passed=False,
            checks=[],
            warnings=[],
            errors=["required file missing: CHANGELOG.md"],
        ),
    )
    exit_code = cli.main(["release", "check"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Final verdict: fail" in output


def test_release_check_no_system_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_release_check",
        lambda: rel.ReleaseCheckReport(passed=True, checks=["all ok"], warnings=[], errors=[]),
    )
    cli.main(["release", "check"])
    output = capsys.readouterr().out
    assert "No package was uploaded." in output
    assert "No global LV2 installation was performed." in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# Infrastructure existence checks
# ---------------------------------------------------------------------------


def test_ci_workflow_exists() -> None:
    ci_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists(), "CI workflow .github/workflows/ci.yml is missing"


def test_fresh_checkout_smoke_script_exists() -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "fresh-checkout-smoke.sh"
    assert script_path.exists(), "scripts/fresh-checkout-smoke.sh is missing"


def test_docs_ci_exists() -> None:
    ci_doc = Path(__file__).resolve().parents[1] / "docs" / "ci.md"
    assert ci_doc.exists(), "docs/ci.md is missing"


def test_docs_release_checklist_exists() -> None:
    checklist = Path(__file__).resolve().parents[1] / "docs" / "release-checklist.md"
    assert checklist.exists(), "docs/release-checklist.md is missing"


# ---------------------------------------------------------------------------
# Build-check hardening — cleanup behavior
# ---------------------------------------------------------------------------


def test_build_check_cleans_dist_after_inspection(monkeypatch) -> None:
    dist_dir_cleaned = []

    original_attempt = pkg._attempt_local_build

    def fake_build():
        dist_dir = pkg.REPO_ROOT / "dist"
        dist_dir.mkdir(exist_ok=True)
        (dist_dir / "fake.whl").write_text("fake", encoding="utf-8")
        result = original_attempt.__wrapped__() if hasattr(original_attempt, "__wrapped__") else None
        dist_dir_cleaned.append(not dist_dir.exists())
        return [], [], []

    # Just verify real build-check no longer leaves dist/ around when build module is available
    import importlib.util
    if importlib.util.find_spec("build") is not None:
        report = pkg.run_package_build_check()
        dist_dir = pkg.REPO_ROOT / "dist"
        # After a successful build-check, dist/ should be cleaned up
        assert not dist_dir.exists(), "build-check left dist/ behind after inspection"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_minimal_repo(root: Path) -> None:
    for name in ("README.md", "CHANGELOG.md", "MANIFEST.in", "LICENSE"):
        (root / name).write_text(name, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "\n".join((
            "[build-system]",
            'requires = ["setuptools>=68", "wheel"]',
            'build-backend = "setuptools.build_meta"',
            "[project]",
            'name = "pipetune-linux"',
            'version = "0.7.1"',
            'description = "test"',
            'readme = "README.md"',
            'requires-python = ">=3.11"',
            'authors = [{ name = "PipeTune Linux Maintainers" }]',
            'license = "MIT"',
            "dependencies = []",
            "[project.scripts]",
            'pipetune = "pipetune.cli:main"',
        )),
        encoding="utf-8",
    )
    plugin_dir = root / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True)
    for fname in pkg.REQUIRED_PLUGIN_SOURCES:
        (plugin_dir / fname).write_text(fname, encoding="utf-8")
    (root / ".gitignore").write_text(
        "\n".join((
            ".venv/",
            "**/__pycache__/",
            ".pytest_cache/",
            "dist/",
            "build/",
            "*.egg-info/",
            "plugins/lv2/**/*.so",
            "plugins/lv2/**/*.o",
        )),
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    for fname in ("install.md", "release-checklist.md"):
        (root / "docs" / fname).write_text(fname, encoding="utf-8")


def _patch_repo_root(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(pkg, "REPO_ROOT", root)
    monkeypatch.setattr(pkg, "PYPROJECT_PATH", root / "pyproject.toml")
    monkeypatch.setattr(pkg, "PLUGIN_SOURCE_DIR", root / "plugins" / "lv2" / "pipetune-safeguard.lv2")
