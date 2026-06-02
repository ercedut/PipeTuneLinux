from __future__ import annotations

from pathlib import Path

from pipetune.models import CommandResult
from pipetune.verify.mic_capture import capture_microphone


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


def test_mic_capture_refuses_without_confirmation() -> None:
    result = capture_microphone(
        duration=5,
        output_path=None,
        confirm_recording=False,
        force=False,
        analyze=False,
    )

    assert result.success is False
    assert result.exit_code != 0
    assert "--confirm-recording" in result.message


def test_mic_capture_validates_duration_range() -> None:
    result_low = capture_microphone(
        duration=0,
        output_path=None,
        confirm_recording=True,
        force=False,
        analyze=False,
    )
    result_high = capture_microphone(
        duration=31,
        output_path=None,
        confirm_recording=True,
        force=False,
        analyze=False,
    )

    assert result_low.success is False
    assert result_high.success is False
    assert "Allowed range" in result_low.message


def test_mic_capture_refuses_overwrite_unless_force(monkeypatch, tmp_path: Path) -> None:
    output_file = tmp_path / "existing.wav"
    output_file.write_bytes(b"x")

    monkeypatch.setattr("pipetune.verify.mic_capture.run_command", lambda *args, **kwargs: _cmd())

    result = capture_microphone(
        duration=5,
        output_path=output_file,
        confirm_recording=True,
        force=False,
        analyze=False,
    )

    assert result.success is False
    assert "Refusing to overwrite" in result.message


def test_mic_capture_handles_missing_arecord_gracefully(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "pipetune.verify.mic_capture.run_command",
        lambda *args, **kwargs: _cmd(available=False, exit_code=None, error="command not found: arecord"),
    )

    result = capture_microphone(
        duration=5,
        output_path=tmp_path / "out.wav",
        confirm_recording=True,
        force=True,
        analyze=False,
    )

    assert result.success is False
    assert "arecord" in result.message


def test_mic_capture_builds_arecord_command_safely_without_shell(monkeypatch, tmp_path: Path) -> None:
    output_file = tmp_path / "captured.wav"
    calls: list[list[str]] = []

    def fake_run(command, timeout=5.0):
        calls.append(list(command))
        if command[:2] == ["arecord", "--version"]:
            return _cmd(available=True, exit_code=0, stdout="arecord version")
        if command[0] == "arecord" and "-d" in command:
            output_file.write_bytes(b"RIFF....WAVE")
            return _cmd(available=True, exit_code=0, stdout="ok")
        return _cmd(available=True, exit_code=0)

    monkeypatch.setattr("pipetune.verify.mic_capture.run_command", fake_run)

    result = capture_microphone(
        duration=5,
        output_path=output_file,
        confirm_recording=True,
        force=True,
        analyze=False,
    )

    assert result.success is True
    capture_call = calls[1]
    assert capture_call[0] == "arecord"
    assert "-d" in capture_call
    assert str(output_file) in capture_call
