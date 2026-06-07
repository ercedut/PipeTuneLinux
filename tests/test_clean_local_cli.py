"""Tests for v0.7.1 clean-local, improved artifact-check, and profile DB packaging hardening."""

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
# Version check
# ---------------------------------------------------------------------------


def test_version_is_091() -> None:
    assert pipetune.__version__ == "0.9.1"


def test_version_codename_is_wireplumber_or_routing() -> None:
    assert any(kw in pipetune.CODENAME for kw in ("WirePlumber", "Routing", "LV2", "CI", "User", "Install", "Rule", "Integrity"))


# ---------------------------------------------------------------------------
# clean-local — unit tests
# ---------------------------------------------------------------------------


def test_clean_local_dry_run_changes_nothing(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    pycache = tmp_path / "pipetune" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "some.pyc").write_text("", encoding="utf-8")
    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()

    report = pkg.run_package_clean_local(dry_run=True)
    assert report.dry_run is True
    assert pycache.exists(), "dry-run must not delete __pycache__"
    assert pytest_cache.exists(), "dry-run must not delete .pytest_cache"


def test_clean_local_dry_run_lists_planned(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    pycache = tmp_path / "pipetune" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "some.pyc").write_text("", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=True)
    assert any("__pycache__" in p for p in report.planned)


def test_clean_local_removes_pycache(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    pycache = tmp_path / "some_module" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "mod.pyc").write_text("", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=False)
    assert not pycache.exists()
    assert any("__pycache__" in r for r in report.removed)


def test_clean_local_removes_pytest_cache(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()
    (pytest_cache / "v" ).mkdir()

    report = pkg.run_package_clean_local(dry_run=False)
    assert not pytest_cache.exists()
    assert any(".pytest_cache" in r for r in report.removed)


def test_clean_local_removes_egg_info(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    egg_info = tmp_path / "pipetune_linux.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("info", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=False)
    assert not egg_info.exists()
    assert any("egg-info" in r for r in report.removed)


def test_clean_local_removes_dist(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "fake.whl").write_text("wheel", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=False)
    assert not dist_dir.exists()
    assert any("dist" in r for r in report.removed)


def test_clean_local_removes_build(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "lib").mkdir()

    report = pkg.run_package_clean_local(dry_run=False)
    assert not build_dir.exists()
    assert any("build" in r for r in report.removed)


def test_clean_local_removes_compiled_plugin_so(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    plugin_dir = tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    so_file = plugin_dir / "pipetune_safeguard.so"
    so_file.write_text("compiled", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=False)
    assert not so_file.exists()
    assert any(".so" in r for r in report.removed)


def test_clean_local_preserves_profile_database(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    profiles_dir = tmp_path / "profiles" / "headphones"
    profiles_dir.mkdir(parents=True)
    profile_toml = profiles_dir / "example.toml"
    profile_toml.write_text("[metadata]\nprofile_id = 'x'\n", encoding="utf-8")

    pkg.run_package_clean_local(dry_run=False)
    assert profile_toml.exists(), "clean-local must not delete profile database files"


def test_clean_local_preserves_lv2_source_files(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    plugin_dir = tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    source_c = plugin_dir / "pipetune_safeguard.c"
    source_c.write_text("/* C source */", encoding="utf-8")
    makefile = plugin_dir / "Makefile"
    makefile.write_text("all: build", encoding="utf-8")

    pkg.run_package_clean_local(dry_run=False)
    assert source_c.exists(), "clean-local must not delete LV2 source .c file"
    assert makefile.exists(), "clean-local must not delete LV2 Makefile"


def test_clean_local_preserves_docs(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    doc_file = docs_dir / "readme.md"
    doc_file.write_text("docs", encoding="utf-8")

    pkg.run_package_clean_local(dry_run=False)
    assert doc_file.exists(), "clean-local must not delete docs"


def test_clean_local_preserves_tests(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    test_file = tests_dir / "test_something.py"
    test_file.write_text("def test_pass(): pass", encoding="utf-8")

    pkg.run_package_clean_local(dry_run=False)
    assert test_file.exists(), "clean-local must not delete test files"


def test_clean_local_outside_repo_is_skipped(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    # Patch to a sub-path so that tmp_path itself is "outside"
    inner = tmp_path / "inner"
    inner.mkdir()
    _write_minimal_repo_v071(inner)
    monkeypatch.setattr(pkg, "REPO_ROOT", inner)
    monkeypatch.setattr(pkg, "PYPROJECT_PATH", inner / "pyproject.toml")
    monkeypatch.setattr(pkg, "PLUGIN_SOURCE_DIR", inner / "plugins" / "lv2" / "pipetune-safeguard.lv2")

    outside_file = tmp_path / "__pycache__"
    outside_file.mkdir(exist_ok=True)
    (outside_file / "x.pyc").write_text("", encoding="utf-8")

    report = pkg.run_package_clean_local(dry_run=False)
    assert outside_file.exists(), "clean-local must not remove paths outside repo root"


def test_clean_local_nothing_to_remove(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)

    report = pkg.run_package_clean_local(dry_run=False)
    assert report.removed == []
    assert not report.errors


# ---------------------------------------------------------------------------
# clean-local — render
# ---------------------------------------------------------------------------


def test_render_clean_local_dry_run_header() -> None:
    report = pkg.CleanLocalReport(dry_run=True, planned=["__pycache__"], removed=[], skipped=[], errors=[])
    output = pkg.render_clean_local_report(report)
    assert "dry-run" in output
    assert "__pycache__" in output


def test_render_clean_local_removed() -> None:
    report = pkg.CleanLocalReport(dry_run=False, planned=[], removed=["dist", "build"], skipped=[], errors=[])
    output = pkg.render_clean_local_report(report)
    assert "Removed:" in output
    assert "dist" in output
    assert "No package was uploaded." in output


def test_render_clean_local_nothing_to_remove() -> None:
    report = pkg.CleanLocalReport(dry_run=False, planned=[], removed=[], skipped=[], errors=[])
    output = pkg.render_clean_local_report(report)
    assert "Nothing to remove." in output


# ---------------------------------------------------------------------------
# clean-local — CLI integration
# ---------------------------------------------------------------------------


def test_clean_local_cli_dry_run(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_clean_local",
        lambda dry_run=False: pkg.CleanLocalReport(
            dry_run=True, planned=["__pycache__"], removed=[], skipped=[], errors=[]
        ),
    )
    exit_code = cli.main(["package", "clean-local", "--dry-run"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dry-run" in output


def test_clean_local_cli_exits_zero_on_clean(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_clean_local",
        lambda dry_run=False: pkg.CleanLocalReport(
            dry_run=False, planned=[], removed=["dist"], skipped=[], errors=[]
        ),
    )
    exit_code = cli.main(["package", "clean-local"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "No package was uploaded." in output


def test_clean_local_cli_exits_nonzero_on_error(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_clean_local",
        lambda dry_run=False: pkg.CleanLocalReport(
            dry_run=False, planned=[], removed=[], skipped=[], errors=["failed to remove x: Permission denied"]
        ),
    )
    exit_code = cli.main(["package", "clean-local"])
    assert exit_code == 1


def test_clean_local_cli_no_system_mutation(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_clean_local",
        lambda dry_run=False: pkg.CleanLocalReport(
            dry_run=False, planned=[], removed=[], skipped=[], errors=[]
        ),
    )
    cli.main(["package", "clean-local"])
    output = capsys.readouterr().out
    assert "No PipeWire, WirePlumber, ALSA" in output
    assert "No audio routing was changed." in output


# ---------------------------------------------------------------------------
# Artifact-check improvement — suggests clean-local
# ---------------------------------------------------------------------------


def test_artifact_check_suggests_clean_local_for_egg_info(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    egg_info = tmp_path / "pipetune_linux.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("info", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    assert any("clean-local" in w for w in report.warnings)


def test_artifact_check_notes_pycache_informational(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    pycache = tmp_path / "some_mod" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "x.pyc").write_text("", encoding="utf-8")

    report = pkg.run_package_artifact_check()
    # __pycache__ is now informational (check), not a warning
    assert any("__pycache__" in c for c in report.checks)
    assert not any("__pycache__" in w for w in report.warnings)


def test_artifact_check_notes_pytest_cache_informational(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    (tmp_path / ".pytest_cache").mkdir()

    report = pkg.run_package_artifact_check()
    # .pytest_cache is now informational (check), not a warning
    assert any(".pytest_cache" in c for c in report.checks)
    assert not any(".pytest_cache" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Profile DB packaging hardening — build-check
# ---------------------------------------------------------------------------


def test_build_check_verifies_profile_db_present(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    profiles_dir = tmp_path / "profiles" / "headphones"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "example.toml").write_text("[metadata]\nprofile_id='x'\n", encoding="utf-8")
    _write_manifest_with_profiles(tmp_path)

    report = pkg.run_package_build_check()
    profile_checks = [c for c in report.checks if "profile database" in c.lower()]
    assert profile_checks, "build-check must verify profile DB is present"


def test_build_check_errors_on_missing_profile_dir(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)

    report = pkg.run_package_build_check()
    profile_errors = [e for e in report.errors if "profiles" in e.lower()]
    assert profile_errors, "build-check must error when profiles/ directory is missing"


def test_build_check_errors_on_empty_profile_dir(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    (tmp_path / "profiles").mkdir()
    _write_manifest_with_profiles(tmp_path)

    report = pkg.run_package_build_check()
    profile_errors = [e for e in report.errors if "profile" in e.lower()]
    assert profile_errors, "build-check must error when profiles/ has no .toml files"


def test_build_check_errors_on_missing_manifest_toml_include(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    profiles_dir = tmp_path / "profiles" / "headphones"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "example.toml").write_text("[metadata]\n", encoding="utf-8")
    # Write MANIFEST.in WITHOUT the profiles include
    (tmp_path / "MANIFEST.in").write_text("include README.md\n", encoding="utf-8")

    report = pkg.run_package_build_check()
    manifest_errors = [e for e in report.errors if "MANIFEST.in" in e and ".toml" in e]
    assert manifest_errors, "build-check must error when MANIFEST.in is missing profile .toml include"


def test_build_check_verifies_manifest_toml_include(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo_v071(tmp_path)
    _patch_pkg_root(monkeypatch, tmp_path)
    profiles_dir = tmp_path / "profiles" / "headphones"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "example.toml").write_text("[metadata]\n", encoding="utf-8")
    _write_manifest_with_profiles(tmp_path)

    report = pkg.run_package_build_check()
    manifest_checks = [c for c in report.checks if "MANIFEST.in" in c and ".toml" in c]
    assert manifest_checks, "build-check must confirm profile .toml files are in MANIFEST.in"


# ---------------------------------------------------------------------------
# Profile DB TOML not gitignored
# ---------------------------------------------------------------------------


def test_profile_db_toml_not_gitignored() -> None:
    import subprocess
    result = subprocess.run(
        ["git", "check-ignore", "-v", "profiles/headphones/example-autoeq-sennheiser-hd650.toml"],
        cwd=pkg.REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0, (
        f"Profile DB TOML is gitignored (must not be): {result.stdout.strip()}"
    )


def test_plugin_so_is_still_gitignored() -> None:
    import subprocess
    # Write a temp .so file to check git-ignore behavior
    import tempfile, os
    plugin_dir = pkg.REPO_ROOT / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    tmp_so = plugin_dir / "check_gitignore_test.so"
    try:
        tmp_so.write_text("test", encoding="utf-8")
        result = subprocess.run(
            ["git", "check-ignore", "-v", str(tmp_so.relative_to(pkg.REPO_ROOT))],
            cwd=pkg.REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, "LV2 .so files must still be gitignored"
    finally:
        if tmp_so.exists():
            tmp_so.unlink()


# ---------------------------------------------------------------------------
# Release check — clean-local integration
# ---------------------------------------------------------------------------


def test_release_check_warns_with_removable_artifacts(monkeypatch) -> None:
    def fake_artifact_check():
        return pkg.PackageReport(
            passed=True,
            checks=[],
            warnings=["*.egg-info/ directories found (gitignored; run: pipetune package clean-local)"],
            errors=[],
        )
    monkeypatch.setattr(rel, "run_package_artifact_check", fake_artifact_check)
    monkeypatch.setattr(rel, "run_package_build_check", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_inspect", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_smoke_test", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.plugin.safeguard import PluginValidationReport
    monkeypatch.setattr(rel, "run_metadata_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_rt_safety_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.profiles.validator import ProfileDbReport
    monkeypatch.setattr(rel, "run_profile_db_validation", lambda: ProfileDbReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    report = rel.run_release_check()
    assert report.verdict == "warn"
    assert any("clean-local" in w for w in report.warnings)


def test_release_check_recommends_clean_local_message(monkeypatch) -> None:
    def fake_artifact_check():
        return pkg.PackageReport(
            passed=True,
            checks=[],
            warnings=[
                "*.egg-info/ directories found (gitignored; run: pipetune package clean-local)",
                "__pycache__/ directories found; run: pipetune package clean-local",
            ],
            errors=[],
        )
    monkeypatch.setattr(rel, "run_package_artifact_check", fake_artifact_check)
    monkeypatch.setattr(rel, "run_package_build_check", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_inspect", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_smoke_test", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.plugin.safeguard import PluginValidationReport
    monkeypatch.setattr(rel, "run_metadata_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_rt_safety_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.profiles.validator import ProfileDbReport
    monkeypatch.setattr(rel, "run_profile_db_validation", lambda: ProfileDbReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    report = rel.run_release_check()
    combined = " ".join(report.warnings)
    assert "clean-local" in combined
    assert "removable" in combined or "development artifacts" in combined


def test_release_check_fails_with_staged_artifact(monkeypatch) -> None:
    def fake_artifact_check():
        return pkg.PackageReport(
            passed=False,
            checks=[],
            warnings=[],
            errors=["forbidden staged artifact (compiled shared object): plugins/lv2/x.so"],
        )
    monkeypatch.setattr(rel, "run_package_artifact_check", fake_artifact_check)
    monkeypatch.setattr(rel, "run_package_build_check", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_inspect", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_package_smoke_test", lambda: pkg.PackageReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.plugin.safeguard import PluginValidationReport
    monkeypatch.setattr(rel, "run_metadata_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))
    monkeypatch.setattr(rel, "run_rt_safety_validation", lambda: PluginValidationReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    from pipetune.profiles.validator import ProfileDbReport
    monkeypatch.setattr(rel, "run_profile_db_validation", lambda: ProfileDbReport(passed=True, checks=["ok"], warnings=[], errors=[]))

    report = rel.run_release_check()
    assert report.verdict == "fail"


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------


def test_docs_clean_local_section_in_release_checklist() -> None:
    checklist = pkg.REPO_ROOT / "docs" / "release-checklist.md"
    assert checklist.exists()
    text = checklist.read_text(encoding="utf-8")
    assert "clean-local" in text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_minimal_repo_v071(root: Path) -> None:
    for name in ("README.md", "CHANGELOG.md", "LICENSE"):
        (root / name).write_text(name, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "\n".join((
            "[build-system]",
            'requires = ["setuptools>=68", "wheel"]',
            'build-backend = "setuptools.build_meta"',
            "[project]",
            'name = "pipetune-linux"',
            'version = "0.8.0"',
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
    (root / "MANIFEST.in").write_text("include README.md\n", encoding="utf-8")
    plugin_dir = root / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True, exist_ok=True)
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
    (root / "docs").mkdir(exist_ok=True)
    for fname in ("install.md", "release-checklist.md"):
        (root / "docs" / fname).write_text(fname, encoding="utf-8")


def _write_manifest_with_profiles(root: Path) -> None:
    (root / "MANIFEST.in").write_text(
        "\n".join((
            "include README.md",
            "recursive-include profiles *.toml",
            "recursive-include profiles *.md",
            "recursive-include docs *.md",
        )),
        encoding="utf-8",
    )


def _patch_pkg_root(monkeypatch, root: Path) -> None:
    monkeypatch.setattr(pkg, "REPO_ROOT", root)
    monkeypatch.setattr(pkg, "PYPROJECT_PATH", root / "pyproject.toml")
    monkeypatch.setattr(pkg, "PLUGIN_SOURCE_DIR", root / "plugins" / "lv2" / "pipetune-safeguard.lv2")
