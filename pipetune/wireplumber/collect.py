"""Safe read-only data collection for WirePlumber and PipeWire diagnostics."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


_CMD_TIMEOUT = 10
_LANG_ENV = {"LC_ALL": "C", "LANG": "C", "LANGUAGE": "C"}


def _env_with_lang() -> dict[str, str]:
    env = os.environ.copy()
    env.update(_LANG_ENV)
    return env


def run_command(args: list[str], force_lang: bool = False) -> tuple[bool, str]:
    """Run a read-only command. Returns (success, output)."""
    try:
        result = subprocess.run(
            args,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_CMD_TIMEOUT,
            env=_env_with_lang() if force_lang else None,
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr.strip() or result.stdout.strip()
    except FileNotFoundError:
        return False, f"command not found: {args[0]}"
    except subprocess.TimeoutExpired:
        return False, f"command timed out after {_CMD_TIMEOUT}s: {args[0]}"
    except OSError as exc:
        return False, f"OS error running {args[0]}: {exc}"


def collect_service_status(service_name: str) -> tuple[bool | None, str]:
    """Check whether a systemd user service is active. Returns (active, details)."""
    ok, output = run_command(["systemctl", "--user", "is-active", service_name])
    if ok:
        status = output.strip()
        return (status == "active"), status
    if "command not found" in output:
        return None, "systemctl not available"
    return False, output.strip() or "inactive"


def collect_wpctl_status() -> tuple[bool, str]:
    return run_command(["wpctl", "status"])


def collect_pactl_info() -> tuple[bool, str]:
    return run_command(["pactl", "info"], force_lang=True)


def collect_pactl_cards() -> tuple[bool, str]:
    return run_command(["pactl", "list", "cards"], force_lang=True)


def collect_pactl_sinks() -> tuple[bool, str]:
    return run_command(["pactl", "list", "sinks"], force_lang=True)


def collect_pactl_sources() -> tuple[bool, str]:
    return run_command(["pactl", "list", "sources"], force_lang=True)
