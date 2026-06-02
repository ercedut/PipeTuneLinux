from __future__ import annotations

from pathlib import Path

from pipetune import cli


def test_verify_command_group_exists() -> None:
    parser = cli._build_parser()
    args = parser.parse_args(["verify", "mic-plan"])

    assert args.command == "verify"
    assert args.verify_command == "mic-plan"


def test_mic_plan_prints_privacy_and_confirmation_warnings() -> None:
    output = cli.render_mic_verification_plan()

    assert "never records unless `--confirm-recording`" in output
    assert "Generated WAV/JSON files are gitignored." in output
    assert "No system configuration was modified." in output


def test_gitignore_contains_verification_privacy_rules() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "verification/microphone/*.wav" in gitignore
    assert "verification/microphone/*.json" in gitignore
    assert "verification/microphone/*.txt" in gitignore
    assert "!verification/.gitkeep" in gitignore
    assert "!verification/microphone/.gitkeep" in gitignore
