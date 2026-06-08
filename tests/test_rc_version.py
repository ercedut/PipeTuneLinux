"""Tests: version is 1.0.0rc1 internally and CLI displays v1.0.0-rc1."""

import subprocess
import sys

import pipetune


def test_internal_version_is_rc1():
    assert pipetune.__version__ == "1.0.0rc1"


def test_internal_codename():
    assert "Stable Release Candidate" in pipetune.CODENAME


def test_cli_version_displays_rc1():
    result = subprocess.run(
        [sys.executable, "-m", "pipetune", "version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "v1.0.0-rc1" in result.stdout


def test_cli_version_displays_codename():
    result = subprocess.run(
        [sys.executable, "-m", "pipetune", "version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "Stable Release Candidate" in result.stdout
