"""EasyEffects collector."""

from __future__ import annotations

import shutil

from pipetune.collectors.command import run_command


def collect_easyeffects_data() -> dict:
    binary_path = shutil.which("easyeffects")
    installed = binary_path is not None

    version_result = None
    if installed:
        version_result = run_command(["easyeffects", "--version"]).to_dict()

    return {
        "installed": installed,
        "binary_path": binary_path,
        "version": version_result,
    }
