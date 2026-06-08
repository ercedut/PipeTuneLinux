"""Tests: rc fedora-smoke."""

import json
import subprocess
from types import SimpleNamespace

from pipetune.rc.fedora_smoke import (
    FedoraSmokeReport,
    SmokeResult,
    render_fedora_smoke,
    render_fedora_smoke_json,
    run_fedora_smoke,
)


def _make_runner(exit_codes: dict[str, int]):
    def runner(args: list[str]) -> subprocess.CompletedProcess:
        key = " ".join(args)
        code = exit_codes.get(key, 0)
        return subprocess.CompletedProcess(
            args=args, returncode=code, stdout="ok\n", stderr=""
        )
    return runner


def _mock_pass_runner(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=args, returncode=0, stdout="pass\n", stderr="")


def _mock_fail_runner(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error output")


def test_fedora_smoke_runs_with_mock():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    assert isinstance(report, FedoraSmokeReport)
    assert report.results


def test_fedora_smoke_pass_with_all_passing():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    assert report.verdict == "pass"
    assert report.passed


def test_fedora_smoke_fail_when_core_command_fails():
    fail_runner = _make_runner({"version": 1})
    report = run_fedora_smoke(runner=fail_runner)
    assert report.verdict == "fail"
    assert any("pipetune version" in e for e in report.errors)


def test_fedora_smoke_json_parses():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    raw = render_fedora_smoke_json(report)
    parsed = json.loads(raw)
    assert "verdict" in parsed
    assert "passed" in parsed
    assert "results" in parsed
    assert "safety" in parsed


def test_fedora_smoke_json_safety_block():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    parsed = json.loads(render_fedora_smoke_json(report))
    safety = parsed["safety"]
    assert safety["read_only"] is True
    assert safety["modified_system"] is False
    assert safety["changed_routing"] is False
    assert safety["restarted_services"] is False
    assert safety["wrote_user_audio_config"] is False


def test_fedora_smoke_text_render():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    text = render_fedora_smoke(report)
    assert "Fedora KDE Smoke Test" in text
    assert "Verdict:" in text
    assert "No routing was changed." in text


def test_fedora_smoke_service_optional_commands_warn_not_fail():
    def partial_fail_runner(args: list[str]) -> subprocess.CompletedProcess:
        key = " ".join(args)
        if "wireplumber" in key and "audit" in key:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="no wireplumber")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok\n", stderr="")
    report = run_fedora_smoke(runner=partial_fail_runner)
    assert report.verdict in ("pass", "warn")
    bluetooth_fail = any("bluetooth" in e for e in report.errors)
    assert not bluetooth_fail, "bluetooth absence should not cause error"


def test_fedora_smoke_results_have_labels():
    report = run_fedora_smoke(runner=_mock_pass_runner)
    for result in report.results:
        assert result.label
        assert isinstance(result.exit_code, int)
