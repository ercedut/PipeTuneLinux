from __future__ import annotations

from pipetune.hardware.mic_audit import collect_mic_audit
from pipetune.models import CommandResult


def _cmd(
    *,
    available: bool = True,
    exit_code: int | None = 0,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    error: str | None = None,
) -> CommandResult:
    return CommandResult(
        command="mock",
        available=available,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        error=error,
    )


def test_capture_device_present_detected_from_arecord_output(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout="card 0: PCH [HDA], device 0: ALC mic [ALC]\n"),
        ("arecord", "-L"): _cmd(stdout="default\n"),
        ("pactl", "list", "sources"): _cmd(stdout="Source #1\nName: alsa_input.pci-0000_00_1f.3.analog-stereo\nMute: no\nState: RUNNING\n"),
        ("pactl", "list", "sources", "short"): _cmd(stdout="1\talsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    result = collect_mic_audit()
    assert result.alsa_capture_devices_count == 1


def test_default_source_parsed_from_sample_pactl_output(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout=""),
        ("arecord", "-L"): _cmd(stdout=""),
        ("pactl", "list", "sources"): _cmd(stdout="Source #1\nName: alsa_input.pci-0000_00_1f.3.analog-stereo\nMute: yes\nState: SUSPENDED\n"),
        ("pactl", "list", "sources", "short"): _cmd(stdout="1\talsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    result = collect_mic_audit()
    assert result.default_source == "alsa_input.pci-0000_00_1f.3.analog-stereo"
    assert result.default_source_muted is True


def test_missing_capture_command_does_not_crash(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(available=False, exit_code=None, error="command not found: arecord"),
        ("arecord", "-L"): _cmd(available=False, exit_code=None, error="command not found: arecord"),
        ("pactl", "list", "sources"): _cmd(available=False, exit_code=None, error="command not found: pactl"),
        ("pactl", "list", "sources", "short"): _cmd(available=False, exit_code=None, error="command not found: pactl"),
        ("wpctl", "status"): _cmd(available=False, exit_code=None, error="command not found: wpctl"),
        ("pactl", "get-default-source"): _cmd(available=False, exit_code=None, error="command not found: pactl"),
        ("pactl", "info"): _cmd(available=False, exit_code=None, error="command not found: pactl"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    result = collect_mic_audit()
    assert result.alsa_capture_devices_count == 0
    assert result.microphone_status == "unavailable"


def test_does_not_claim_microphone_working_without_capture_test(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout="card 0: PCH [HDA], device 0: ALC mic [ALC]\n"),
        ("arecord", "-L"): _cmd(stdout="default\n"),
        ("pactl", "list", "sources"): _cmd(stdout="Source #1\nName: alsa_input.pci-0000_00_1f.3.analog-stereo\nMute: no\nState: RUNNING\n"),
        ("pactl", "list", "sources", "short"): _cmd(stdout="1\talsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    result = collect_mic_audit()

    assert result.capture_test_performed is False
    assert "does not prove microphone functionality" in result.safety_recommendation.lower()
