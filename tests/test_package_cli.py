from __future__ import annotations

import subprocess
from pathlib import Path

from pipetune import cli
from pipetune import packaging as pkg


def _write_minimal_project(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pipetune-linux"
version = "0.9.2"
description = "test"
readme = "README.md"
requires-python = ">=3.11"
authors = [{ name = "PipeTune Linux Maintainers" }]
license = "MIT"
dependencies = []

[project.scripts]
pipetune = "pipetune.cli:main"
""",
        encoding="utf-8",
    )
    for file_name in ("README.md", "LICENSE", "CHANGELOG.md", "MANIFEST.in"):
        (root / file_name).write_text(file_name, encoding="utf-8")
    plugin_dir = root / "plugins" / "lv2" / "pipetune-safeguard.lv2"
    plugin_dir.mkdir(parents=True)
    for file_name in pkg.REQUIRED_PLUGIN_SOURCES:
        (plugin_dir / file_name).write_text(file_name, encoding="utf-8")
    (root / ".gitignore").write_text(
        "\n".join(
            (
                ".venv/",
                "**/__pycache__/",
                ".pytest_cache/",
                "dist/",
                "build/",
                "*.egg-info/",
                "plugins/lv2/**/*.so",
                "plugins/lv2/**/*.o",
            )
        ),
        encoding="utf-8",
    )


def test_package_inspect_cli_reports_project_metadata(capsys) -> None:
    exit_code = cli.main(["package", "inspect"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "PipeTune Package Inspect" in output
    assert "package name: pipetune-linux" in output
    assert "project version: 1.0.0rc1" in output
    assert "CLI entry point configured: yes" in output
    assert "plugin source bundle present: yes" in output
    assert "No PipeWire, WirePlumber, ALSA, service, system, or user audio configuration was modified." in output


def test_package_build_check_handles_missing_build_module(capsys, monkeypatch) -> None:
    monkeypatch.setattr(pkg.importlib.util, "find_spec", lambda name: None if name == "build" else object())

    exit_code = cli.main(["package", "build-check"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "python build module is not installed" in output
    assert "python -m pip install build" in output
    assert "No package was uploaded." in output


def test_package_build_check_detects_forbidden_plugin_artifacts(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_project(tmp_path)
    (tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2" / "pipetune_safeguard.so").write_text(
        "compiled",
        encoding="utf-8",
    )
    monkeypatch.setattr(pkg, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(pkg, "PYPROJECT_PATH", tmp_path / "pyproject.toml")
    monkeypatch.setattr(pkg, "PLUGIN_SOURCE_DIR", tmp_path / "plugins" / "lv2" / "pipetune-safeguard.lv2")
    monkeypatch.setattr(pkg.importlib.util, "find_spec", lambda name: None if name == "build" else object())

    report = pkg.run_package_build_check()

    assert report.passed is False
    assert any("Forbidden local artifacts detected" in error for error in report.errors)


def test_archive_forbidden_check_rejects_compiled_lv2_artifacts() -> None:
    forbidden = pkg.build_archive_forbidden_check_fixture(
        [
            "pipetune_linux-0.6.0/plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.so",
            "pipetune_linux-0.6.0/plugins/lv2/pipetune-safeguard.lv2/pipetune_safeguard.o",
            "pipetune_linux-0.6.0/pipetune/cli.py",
        ]
    )

    assert any(item.endswith("pipetune_safeguard.so") for item in forbidden)
    assert any(item.endswith("pipetune_safeguard.o") for item in forbidden)


def test_package_smoke_test_with_runner_passes() -> None:
    def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    report = pkg.run_package_smoke_test_with_runner(runner)
    rendered = pkg.render_package_report("Smoke", report)

    assert report.passed is True
    assert "pipetune version: pass" in rendered
    assert "pipetune plugin validate --metadata: pass" in rendered
    assert "smoke-test commands are non-mutating checks only" in rendered


def test_package_smoke_test_cli_uses_non_mutating_disclaimer(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        "pipetune.cli.run_package_smoke_test",
        lambda: pkg.PackageReport(
            passed=True,
            checks=["pipetune version: pass", "smoke-test commands are non-mutating checks only"],
            warnings=[],
            errors=[],
        ),
    )

    exit_code = cli.main(["package", "smoke-test"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Final verdict: pass" in output
    assert "No package was uploaded." in output
    assert "No audio routing was changed." in output
