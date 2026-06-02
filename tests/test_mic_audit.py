from __future__ import annotations

from pipetune.hardware.mic_audit import (
    _extract_source_counts_from_long,
    _extract_source_counts_from_short,
    collect_mic_audit,
    render_mic_audit_summary,
)
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


def test_short_source_count_classifies_one_input_source() -> None:
    output = "1\talsa_input.pci-0000_00_1f.3.analog-stereo\tPipeWire\tfloat32le 2ch 48000Hz\tSUSPENDED\n"

    input_count, monitor_count, total_count = _extract_source_counts_from_short(output)

    assert input_count == 1
    assert monitor_count == 0
    assert total_count == 1


def test_short_source_count_classifies_monitor_source() -> None:
    output = "2\talsa_output.pci-0000_00_1f.3.analog-stereo.monitor\tPipeWire\tfloat32le 2ch 48000Hz\tSUSPENDED\n"

    input_count, monitor_count, total_count = _extract_source_counts_from_short(output)

    assert input_count == 0
    assert monitor_count == 1
    assert total_count == 1


def test_long_source_count_counts_source_blocks_only() -> None:
    output = """
Source #1
    State: SUSPENDED
    Name: alsa_input.pci-0000_00_1f.3.analog-stereo
Source #2
    State: SUSPENDED
    Name: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
Source Output #99
    Source: 1
    Client: 22
"""

    input_count, monitor_count, total_count = _extract_source_counts_from_long(output)

    assert input_count == 1
    assert monitor_count == 1
    assert total_count == 2


def test_long_source_count_handles_no_sources() -> None:
    assert _extract_source_counts_from_long("Source Output #1\nSource: 0\n") == (0, 0, 0)


def test_source_output_text_is_not_counted_as_source() -> None:
    input_count, monitor_count, total_count = _extract_source_counts_from_long(
        "Source Output #7\n    Source: 1\n    Client: 99\n"
    )

    assert input_count == 0
    assert monitor_count == 0
    assert total_count == 0


def test_mic_audit_output_reports_input_monitor_and_total_counts(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout=""),
        ("arecord", "-L"): _cmd(stdout="default\n"),
        ("pactl", "list", "sources"): _cmd(
            stdout="""
Source #1
    Name: alsa_input.pci-0000_00_1f.3.analog-stereo
    Mute: no
    State: SUSPENDED
Source #2
    Name: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
Source Output #82
    Source: 1
"""
        ),
        ("pactl", "list", "sources", "short"): _cmd(stdout=""),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    output = render_mic_audit_summary(collect_mic_audit())

    assert "Input sources: 1" in output
    assert "Monitor sources: 1" in output
    assert "Total sources: 2" in output
    assert "82" not in output


def test_default_source_visible_with_failed_source_enumeration_reports_unknown(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout=""),
        ("arecord", "-L"): _cmd(stdout="default\n"),
        ("pactl", "list", "sources"): _cmd(stdout="Source #1\n    State: SUSPENDED\n"),
        ("pactl", "list", "sources", "short"): _cmd(stdout="not-a-source-line\n"),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    result = collect_mic_audit()
    output = render_mic_audit_summary(result)

    assert result.input_sources_count is None
    assert result.monitor_sources_count is None
    assert result.total_sources_count is None
    assert "PipeWire/Pulse sources: unknown (default source is visible)" in output
    assert "Total sources: 0" not in output


def test_default_source_visible_with_empty_enumeration_reports_unknown(monkeypatch) -> None:
    mapping = {
        ("arecord", "-l"): _cmd(stdout=""),
        ("arecord", "-L"): _cmd(stdout="default\n"),
        ("pactl", "list", "sources"): _cmd(stdout=""),
        ("pactl", "list", "sources", "short"): _cmd(stdout=""),
        ("wpctl", "status"): _cmd(stdout="Audio\n"),
        ("pactl", "get-default-source"): _cmd(stdout="alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
        ("pactl", "info"): _cmd(stdout="Default Source: alsa_input.pci-0000_00_1f.3.analog-stereo\n"),
    }

    def fake_run(command, timeout=5.0):
        return mapping[tuple(command)]

    monkeypatch.setattr("pipetune.hardware.mic_audit.run_command", fake_run)

    output = render_mic_audit_summary(collect_mic_audit())

    assert "PipeWire/Pulse sources: unknown (default source is visible)" in output
    assert "Total sources: 0" not in output
