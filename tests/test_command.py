from __future__ import annotations

import sys

from pipetune.collectors.command import run_command


def test_missing_command_does_not_crash() -> None:
    result = run_command(["definitely_not_a_real_command_12345"])
    assert result.available is False
    assert result.exit_code is None
    assert result.error is not None


def test_timeout_is_handled() -> None:
    result = run_command([sys.executable, "-c", "import time; time.sleep(2)"], timeout=0.1)
    assert result.available is True
    assert result.timed_out is True
    assert result.error is not None


def test_successful_command_returns_stdout() -> None:
    result = run_command([sys.executable, "-c", "print('ok')"])
    assert result.available is True
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
