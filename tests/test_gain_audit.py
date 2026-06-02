from __future__ import annotations

from pipetune import cli
from pipetune.gain.gain_audit import collect_gain_audit, render_gain_audit
from pipetune.models import CommandResult


def _result(command: list[str], stdout: str, *, available: bool = True, exit_code: int | None = 0) -> CommandResult:
    return CommandResult(
        command=" ".join(command),
        available=available,
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        timed_out=False,
        error=None if available else "missing",
    )


def test_gain_audit_command_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["hardware", "gain-audit"])

    assert args.command == "hardware"
    assert args.hardware_command == "gain-audit"


def test_gain_audit_collects_read_only_state(monkeypatch) -> None:
    outputs = {
        ("pactl", "get-default-source"): "alsa_input.test\n",
        ("pactl", "get-source-volume", "@DEFAULT_SOURCE@"): "Volume: front-left: 52429 / 80% / -5.81 dB\n",
        ("pactl", "get-source-mute", "@DEFAULT_SOURCE@"): "Mute: no\n",
        ("wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"): "Volume: 0.80\n",
        ("amixer", "-c", "0", "scontrols"): "Simple mixer control 'Capture',0\nSimple mixer control 'Mic Boost',0\n",
        ("amixer", "-c", "0"): """
Simple mixer control 'Capture',0
  Front Left: Capture 42 [67%] [12.00dB] [on]
Simple mixer control 'Mic Boost',0
  Mono: 0 [0%] [0.00dB]
""",
    }

    def fake_run_command(command):
        return _result(command, outputs.get(tuple(command), ""))

    monkeypatch.setattr("pipetune.gain.gain_audit.run_command", fake_run_command)

    audit = collect_gain_audit()
    output = render_gain_audit(audit)

    assert audit.default_source == "alsa_input.test"
    assert audit.default_source_muted is False
    assert "Pulse/PipeWire volume: 80%" in output
    assert "Capture: detected" in output
    assert "No system configuration was modified." in output


def test_gain_audit_missing_tools_do_not_crash(monkeypatch) -> None:
    def fake_run_command(command):
        return _result(command, "", available=False, exit_code=None)

    monkeypatch.setattr("pipetune.gain.gain_audit.run_command", fake_run_command)

    output = render_gain_audit(collect_gain_audit())

    assert "unknown" in output
    assert "No system configuration was modified." in output
