"""Safe command execution for read-only diagnostics."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from typing import Sequence

from pipetune.models import CommandResult

DEFAULT_TIMEOUT_SECONDS = 5.0


def run_command(command: Sequence[str], timeout: float = DEFAULT_TIMEOUT_SECONDS) -> CommandResult:
    """Execute a command safely and return structured results.

    This helper is read-only and never raises command execution failures as fatal
    exceptions to callers.
    """
    rendered = " ".join(shlex.quote(part) for part in command)
    if not command:
        return CommandResult(
            command=rendered,
            available=False,
            exit_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            error="empty command",
        )

    executable = command[0]
    is_path_like = "/" in executable
    if not is_path_like and shutil.which(executable) is None:
        return CommandResult(
            command=rendered,
            available=False,
            exit_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            error=f"command not found: {executable}",
        )

    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            command=rendered,
            available=True,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
            error=None,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(
            command=rendered,
            available=True,
            exit_code=None,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            error=f"timed out after {timeout} seconds",
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        return CommandResult(
            command=rendered,
            available=True,
            exit_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            error=str(exc),
        )
